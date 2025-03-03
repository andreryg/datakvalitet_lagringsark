from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from flaskr.db import get_db
import requests
import tqdm
bp = Blueprint('views', __name__)

@bp.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        pass
    return render_template('views/index.html')

@bp.route('/add_data', methods=('GET', 'POST'))
def add_data():
    print("dddddd")
    db = get_db()

    datakatalog = requests.get("https://nvdbapiles.atlas.vegvesen.no/vegobjekttyper").json()
    
    egenskapstyper = []
    for vegobjekttype in datakatalog:
        egenskapstyper += [dict(egenskapstype, vtid=vegobjekttype.get('id')) for egenskapstype in vegobjekttype.get('egenskapstyper') if egenskapstype.get('id') < 200000]
    db.executemany(
        "INSERT OR IGNORE INTO vegobjekttype (id, navn, hovedkategori) VALUES (?, ?, ?)",
        [(vegobjekttype.get('id'), vegobjekttype.get('navn'), vegobjekttype.get('hovedkategori')) for vegobjekttype in datakatalog]
        )
    db.executemany(
        "INSERT OR IGNORE INTO egenskapstype (id, navn, vegobjekttype_id, datatype, viktighet) VALUES (?, ?, ?, ?, ?)",
        [(egenskapstype.get('id'), egenskapstype.get('navn'), egenskapstype.get('vtid'), egenskapstype.get('egenskapstype'), egenskapstype.get('viktighet')) for egenskapstype in egenskapstyper]
        )
    db.commit()
    return redirect(url_for('views.index'))

@bp.route('/add_kvalitetsmålinger', methods=('GET', 'POST'))
def add_kvalitetsmålinger():
    from flaskr.automatisk_registrering import Automatisk_registrer_kvalitet
    db = get_db()
    vegobjekttyper = db.execute(
        "SELECT id as vt_id FROM vegobjekttype"
        ).fetchall()
    
    vegobjekttyper = [dict(row) for row in vegobjekttyper]
    for vegobjekttype in vegobjekttyper:
        if vegobjekttype['vt_id'] == 470:
            kvalitet = Automatisk_registrer_kvalitet(vegobjekttype['vt_id'])
    
    db.commit()
    return redirect(url_for('views.index'))

@bp.route('/aggreger', methods=('GET', 'POST'))
def aggreger():
    from flaskr.aggregering import aggreger_område, aggreger_vegobjekttype
    db = get_db()
    kvalitetselementer = db.execute(
        "SELECT * FROM kvalitetselement"
    ).fetchall()
    kvalitetselementer = [dict(row) for row in kvalitetselementer]
    for kvalitetselement in tqdm.tqdm(kvalitetselementer):
        if kvalitetselement['id'] in [13, 14, 15]:
            aggreger_område(kvalitetselement['id'])
            aggreger_vegobjekttype(kvalitetselement['id'])
        elif kvalitetselement['id'] in [30, 58, 59, 62]:
            aggreger_område(kvalitetselement['id'])
    return redirect(url_for('views.index'))

@bp.route('/kvalitetregistrering', methods=('GET', 'POST'))
def add_kvalitetregistrering():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            "INSERT INTO kvalitetsmåling (kvalitetsnivå_1, kvalitetsnivå_2, kvalitetsnivå_3, vegobjekttype_id, egenskapstype_id, verdi, dato, område_id) VALUES (?, ?, ?, ?, ?, ? ,?, ?)",
            (request.form['kvalitetsnivå_1'], request.form['kvalitetsnivå_2'], request.form['kvalitetsnivå_3'], request.form['vegobjekttype_id'], request.form['egenskapstype_id'], request.form['verdi'], request.form['dato'], request.form['område_id'])
            )
        db.commit()
        return redirect(url_for('views.add_kvalitetregistrering'))
    return render_template('views/kvalitetregistrering.html')
    
@bp.route('/kvalitetark', methods=('GET', 'POST'))
@bp.route('/kvalitetark/vegobjekttype/<string:vtid>', methods=('GET', 'POST'))
@bp.route('/kvalitetark/vegobjekttype/<string:vtid>/område/<string:omrade_id>', methods=('GET', 'POST'))
def datakvalitet_kvalitetark(vtid = None, omrade_id = None):
    if request.method == 'GET':
        db = get_db()
        vegobjekttyper = db.execute(
            """SELECT * FROM vegobjekttype"""
        ).fetchall()
        vegobjekttyper = [dict(row) for row in vegobjekttyper]
        vegobjekttyper_ = [(r['id'], str(r['id']) + ' - ' + r['navn']) for r in vegobjekttyper]

        if vtid is not None:
            vegstrekninger = db.execute(
                """SELECT vegsystem_id, vegstrekning, fylke_id, kommune_id, navn, vegstrekning.id 
                FROM vegstrekning
                join kvalitetsmåling on vegstrekning.id = kvalitetsmåling.vegstrekning_id
                join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
                where kvalitetsmåling.vegobjekttype_id = ?
                order by vegkategori_id, vegnummer, CAST(SUBSTR(vegstrekning, 2) AS INTEGER)""",
                (vtid,)
            ).fetchall()
            vegstrekninger = [dict(row) for row in vegstrekninger]
        
        if vtid is not None and omrade_id is not None:
            egenskapstyper = db.execute(
                """SELECT * FROM egenskapstype"""
            ).fetchall()
            egenskapstyper = [dict(row) for row in egenskapstyper]
            kvalitetselement = db.execute(
                """select kvalitetselement.id, kvalitetsnivå_1.navn || "." || kvalitetsnivå_2.navn || "." || kvalitetselement.navn as navn, kvalitetselement.kvalitetsnivå_1, kvalitetselement.kvalitetsnivå_2, kvalitetselement.kvalitetsnivå_3 
                from kvalitetselement
                join kvalitetsnivå_1 on kvalitetselement.kvalitetsnivå_1 = kvalitetsnivå_1.id
                join kvalitetsnivå_2 on kvalitetselement.kvalitetsnivå_2 = kvalitetsnivå_2.id"""
            ).fetchall()
            kvalitetselement = [dict(row) for row in kvalitetselement]
            vegobjektnavn = next((i.get('navn') for i in vegobjekttyper if i.get('id') == vtid),'Noe galt har skjedd')
            områdenavn = next((i.get('navn') for i in vegstrekninger if i.get('id') == omrade_id), 'Noe galt har skjedd')
            kvalitetsmålinger = db.execute(
                """SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, kvalitetsmåling.vegstrekning_id, kvalitetsmåling.verdi, kvalitetsmåling.dato 
                FROM kvalitetsmåling
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                WHERE kvalitetsmåling.vegobjekttype_id = ? AND kvalitetsmåling.vegstrekning_id = ?
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
                (vtid, omrade_id)
                ).fetchall()
            kvalitetsmålinger = [dict(row) for row in kvalitetsmålinger]
            kvalitetselement_relevant_ider = list(set([str(item['kvid']) for item in kvalitetsmålinger]))
            referanseverdier = db.execute(
                """SELECT referanseverdi.kvalitetselement_id AS kvid, referanseverdi.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, referanseverdi.vegstrekning_id, referanseverdi.verdi, referanseverdi.dato 
                FROM referanseverdi
                INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
                WHERE referanseverdi.vegobjekttype_id = ? AND referanseverdi.vegstrekning_id = ?
                ORDER BY referanseverdi.vegobjekttype_id""",
                (vtid, omrade_id)
                ).fetchall()
            referanseverdier = [dict(row) for row in referanseverdier]
            skala = db.execute(
                """SELECT * FROM skala"""
            ).fetchall()
            skala = [dict(row) for row in skala]
            return render_template('views/kvalitetark.html', vtid=vtid, omrade_id=omrade_id, vegobjekttyper_=vegobjekttyper_, vegobjekttyper=vegobjekttyper, egenskapstyper=egenskapstyper, områder=vegstrekninger, kvalitetselementer=kvalitetselement, kvalitetselement_relevant_ider=kvalitetselement_relevant_ider, kvalitetsmålinger=kvalitetsmålinger, referanseverdier=referanseverdier, skala=skala)

        if vtid is not None:
            return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_, områder=vegstrekninger, vtid=vtid)
        return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_)

    if request.method == 'POST':
        vtid_filter = request.form.get('vtid')
        område_filter = request.form.get('område')
        if vtid_filter is not None and område_filter is None:
            vtid = request.form['vegobjekttyper']
            return redirect(url_for('views.datakvalitet_kvalitetark', vtid=vtid))
        omrade_id = request.form['områder']
        return redirect(url_for('views.datakvalitet_kvalitetark', vtid=vtid, omrade_id=omrade_id))
    
@bp.route("/add_område", methods=('GET', 'POST'))
def add_område():
    jason = request.get_json()
    vtid = jason[0]
    område_id = jason[1]
    db = get_db()
    sammenlign_kvalitetsmålinger = db.execute(
        """SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, kvalitetsmåling.vegstrekning_id, kvalitetsmåling.verdi, kvalitetsmåling.dato 
        FROM kvalitetsmåling
        INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
        LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
        WHERE kvalitetsmåling.vegobjekttype_id = ? AND kvalitetsmåling.vegstrekning_id = ?
        ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
        (vtid, område_id)
        ).fetchall()
    sammenlign_kvalitetsmålinger = [dict(row) for row in sammenlign_kvalitetsmålinger]
    sammenlign_referanseverdier = db.execute(
        """SELECT referanseverdi.kvalitetselement_id AS kvid, referanseverdi.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, referanseverdi.vegstrekning_id, referanseverdi.verdi, referanseverdi.dato 
        FROM referanseverdi
        INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
        WHERE referanseverdi.vegobjekttype_id = ? AND referanseverdi.vegstrekning_id = ?
        ORDER BY referanseverdi.vegobjekttype_id""",
        (vtid, område_id)
        ).fetchall()
    sammenlign_referanseverdier = [dict(row) for row in sammenlign_referanseverdier]
    jason_2 = {'sammenlign_kvalitetsmålinger': sammenlign_kvalitetsmålinger, 'sammenlign_referanseverdier': sammenlign_referanseverdier}
    return jason_2