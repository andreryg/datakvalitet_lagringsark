from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from flaskr.db import get_db
from flaskr.aggregering import aggreger_vegstrekninger
import requests
import tqdm
from flaskr.hent_data import hent_data, hent_historisk_data
from flaskr.generer_label import generer_label
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
        if vegobjekttype['vt_id'] == 3:
            kvalitet = Automatisk_registrer_kvalitet(vegobjekttype['vt_id'])
    
    db.commit()
    return redirect(url_for('views.index'))

@bp.route('/aggreger', methods=('GET', 'POST'))
def aggreger():
    hent_data("3", "E", "0", "0", "0", "0")
    """from flaskr.aggregering import aggreger_område, aggreger_vegobjekttype
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
            aggreger_område(kvalitetselement['id'])"""
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
@bp.route('/kvalitetark/vegobjekttype/<string:vtid>/<string:vegkategori>/<string:vegsystem_id>/<string:fylke_id>/<string:kommune_id>/<string:omrade_id>', methods=('GET', 'POST'))
def datakvalitet_kvalitetark(vtid = None, omrade_id = None, vegkategori = None, vegsystem_id = None, fylke_id = None, kommune_id = None):
    if request.method == 'GET':
        db = get_db()
        vegobjekttyper = db.execute(
            """SELECT * FROM vegobjekttype"""
        ).fetchall()
        vegobjekttyper = [dict(row) for row in vegobjekttyper]
        vegobjekttyper_ = [(r['id'], str(r['id']) + ' - ' + r['navn']) for r in vegobjekttyper]

        if vtid is not None:
            #Aggregerte områder legges til i vegstrekninger i dannelsen av db, hvis de velger må spesifiserte spørringer kjøres.
            vegstrekninger = db.execute(
                """SELECT DISTINCT vegsystem_id, vegstrekning, vegstrekning.fylke_id, vegstrekning.kommune_id, vegstrekning.navn, vegstrekning.id, vegkategori.kortnavn, fylke.navn as fylke, kommune.navn as kommune
                FROM vegstrekning
                join kvalitetsmåling on vegstrekning.id = kvalitetsmåling.vegstrekning_id
                join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
                join vegkategori on vegsystem.vegkategori_id = vegkategori.id
                join fylke on vegstrekning.fylke_id = fylke.id
                left join kommune on vegstrekning.kommune_id = kommune.id
                where kvalitetsmåling.vegobjekttype_id = ?
                order by vegkategori_id, vegnummer, CAST(SUBSTR(vegstrekning, 2) AS INTEGER)""",
                (vtid,)
            ).fetchall()
            vegstrekninger = [dict(row) for row in vegstrekninger]
            vegkategorier = list(set(vegstrekning.get('kortnavn') for vegstrekning in vegstrekninger))
            vegsystemer = [{'id':vegstrekning.get('vegsystem_id'),'navn':vegstrekning.get('navn').split()[0]} for vegstrekning in vegstrekninger]
            vegsystemer = [i for n, i in enumerate(vegsystemer) if i not in vegsystemer[n + 1:]]
            fylker = [{'id':vegstrekning.get('fylke_id'),'navn':vegstrekning.get('fylke')} for vegstrekning in vegstrekninger if vegstrekning.get('fylke_id') != 0]
            fylker = [i for n, i in enumerate(fylker) if i not in fylker[n + 1:]]
            kommuner = [{'id':vegstrekning.get('kommune_id'),'navn':vegstrekning.get('kommune')} for vegstrekning in vegstrekninger if vegstrekning.get('kommune_id') != 0]
            kommuner = [i for n, i in enumerate(kommuner) if i not in kommuner[n + 1:]]

        if vtid is not None and not all(x is None for x in [vegkategori, vegsystem_id, fylke_id, kommune_id, omrade_id]):
            område_navn = generer_label(omrade_id, vegkategori, vegsystem_id, fylke_id, kommune_id)
            område_id = '&'.join([str(vegkategori),str(vegsystem_id),str(fylke_id),str(kommune_id),str(omrade_id)])
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
            kvalitetsmålinger = hent_data(vtid, vegkategori, vegsystem_id, fylke_id, kommune_id, omrade_id)
            kvalitetselement_relevante_ider = list(set([item['kvid'] for item in kvalitetsmålinger]))
            skala = db.execute(
                """SELECT * FROM skala"""
            ).fetchall()
            skala = [dict(row) for row in skala]
            print(område_id)
            return render_template('views/kvalitetark.html', vtid=vtid, omrade_id=område_id, vegobjekttyper_=vegobjekttyper_, vegobjekttyper=vegobjekttyper, egenskapstyper=egenskapstyper, områder=vegstrekninger, kvalitetselementer=kvalitetselement, kvalitetselement_relevant_ider=kvalitetselement_relevante_ider, kvalitetsmålinger=kvalitetsmålinger, skala=skala, vegkategorier=vegkategorier, vegsystemer=vegsystemer, fylker=fylker, kommuner=kommuner, område_navn=område_navn)

        if vtid is not None:
            return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_, områder=vegstrekninger, vtid=vtid, vegkategorier=vegkategorier, vegsystemer=vegsystemer, fylker=fylker, kommuner=kommuner)
        return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_)

    if request.method == 'POST':
        vtid_filter = request.form.get('vtid')
        område_filter = request.form.get('område')
        if vtid_filter is not None and område_filter is None:
            vtid = request.form['vegobjekttyper']
            return redirect(url_for('views.datakvalitet_kvalitetark', vtid=vtid))
        vegkategori = request.form.get('vegkategorier')
        vegsystem_id = request.form.get('vegsystemer')
        fylke_id = request.form.get('fylker')
        kommune_id = request.form.get('kommuner')
        omrade_id = request.form.get('områder')
        print(vegkategori, vegsystem_id, fylke_id, kommune_id, omrade_id)
        return redirect(url_for('views.datakvalitet_kvalitetark', vtid=vtid, omrade_id=omrade_id, vegkategori=vegkategori, vegsystem_id=vegsystem_id, fylke_id=fylke_id, kommune_id=kommune_id))
    
@bp.route("/add_område", methods=('GET', 'POST'))
def add_område():
    jason = request.get_json()
    vtid = jason[0]
    sammenlign_filter = jason[1].split("&")
    vegkategori = sammenlign_filter[0]
    vegsystem_id = sammenlign_filter[1]
    fylke_id = sammenlign_filter[2]
    kommune_id = sammenlign_filter[3]
    område_id = sammenlign_filter[4]
    område_navn = generer_label(område_id, vegkategori, vegsystem_id, fylke_id, kommune_id)
    kvalitetsmålinger = hent_data(vtid, vegkategori, vegsystem_id, fylke_id, kommune_id, område_id)
    return {'sammenlign_kvalitetsmålinger':kvalitetsmålinger, 'område_navn':område_navn}

@bp.route("/linjediagram", methods=('GET', 'POST'))
def linjediagram():
    jason = request.get_json()
    print(jason)
    vtid = jason.get('vtid')
    sammenlign_filter = jason.get('område').replace("amp;", "").split("&")
    vegkategori = sammenlign_filter[0]
    vegsystem_id = sammenlign_filter[1]
    fylke_id = sammenlign_filter[2]
    kommune_id = sammenlign_filter[3]
    område_id = sammenlign_filter[4]
    if jason.get('egenskapsnivå'):
        et_navn = jason.get('egenskap')
    else:
        et_navn = None
    kvid = int(jason.get('kvalitetselement'))

    område1_navn = generer_label(område_id, vegkategori, vegsystem_id, fylke_id, kommune_id)
    dataset1 = hent_historisk_data(vtid, et_navn, kvid, vegkategori, vegsystem_id, fylke_id, kommune_id, område_id)
    dataset1 = [{'x': item['dato'], 'y': item['verdi']/item['ref_verdi']*100} for item in dataset1]
    dataset2 = None
    if jason.get('område2'):
        sammenlign_filter = jason.get('område2').replace("amp;", "").split("&")
        vegkategori = sammenlign_filter[0]
        vegsystem_id = sammenlign_filter[1]
        fylke_id = sammenlign_filter[2]
        kommune_id = sammenlign_filter[3]
        område_id = sammenlign_filter[4]
        område2_navn = generer_label(område_id, vegkategori, vegsystem_id, fylke_id, kommune_id)
        dataset2 = hent_historisk_data(vtid, et_navn, kvid, vegkategori, vegsystem_id, fylke_id, kommune_id, område_id)
        dataset2 = [{'x': item['dato'], 'y': item['verdi']/item['ref_verdi']*100} for item in dataset2]
    return {'dataset1':dataset1, 'dataset2':dataset2, 'labels':[jason.get('egenskap'), kvid, område1_navn, område2_navn] if dataset2 else [jason.get('egenskap'), kvid, område1_navn]}