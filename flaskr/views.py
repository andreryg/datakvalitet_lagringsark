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
        "SELECT id as vt_id FROM vegobjekttype LIMIT 3"
        ).fetchall()
    
    vegobjekttyper = [dict(row) for row in vegobjekttyper]
    for vegobjekttype in vegobjekttyper:
        if vegobjekttype['vt_id'] == 3:
            kvalitet = Automatisk_registrer_kvalitet(vegobjekttype['vt_id'])
            kvalitet.hent_kvalitetsmåling()

    """ områder = db.execute(
        "SELECT * FROM område WHERE fylke_id IS NOT NULL AND vegsystem_id > 2"
        ).fetchall()

    for område in områder:
        print(område["navn"])
        for vegobjekttype in vegobjekttyper:
            sjekk = db.execute(
                "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                (7, område["id"], vegobjekttype["vt_id"], 0)#vegobjekttype["et_id"]
                ).fetchone()
            if not sjekk:
                kvalitet = Automatisk_registrer_kvalitet(7, område["id"], vegobjekttype["vt_id"], 0)
                kvalitet.hent_kvalitet()
                kvalitet.hent_referanseverdi()
                kvalitet.registrer_kvalitet() """
    
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

@bp.route('/datakvalitet/tabell', methods=('GET', 'POST'))
def datakvalitet():
    if request.method == 'GET':
        db = get_db()
        kvalitetsmålinger = db.execute(
            """SELECT kvalitetselement.navn AS ke_navn, kvalitetsmåling.vegobjekttype_id, vegobjekttype.navn AS vt_navn, kvalitetsmåling.egenskapstype_id, egenskapstype.navn AS et_navn, område.navn AS område, kvalitetsmåling.verdi, kvalitetsmåling.dato 
            FROM kvalitetsmåling
            INNER JOIN kvalitetselement ON kvalitetsmåling.kvalitetsnivå_1 = kvalitetselement.kvalitetsnivå_1
            AND kvalitetsmåling.kvalitetsnivå_2 = kvalitetselement.kvalitetsnivå_2
            AND kvalitetsmåling.kvalitetsnivå_3 = kvalitetselement.kvalitetsnivå_3
            INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
            INNER JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
            INNER JOIN område ON kvalitetsmåling.område_id = område.id"""
            ).fetchall()
        print([r for r in kvalitetsmålinger[0]])
        return render_template('views/datakvalitet.html', kvalitetsmålinger=kvalitetsmålinger)

@bp.route('/datakvalitet/vegobjekttype', methods=('GET', 'POST'))
@bp.route('/datakvalitet/vegobjekttype/<string:id>', methods=('GET', 'POST'))
def datakvalitet_vegobjekttype(id = None):
    if request.method == 'GET':
        db = get_db()
        if id is not None:
            kvalitetsmålinger = db.execute(
                """SELECT kvalitetselement.navn AS ke_navn, kvalitetsmåling.vegobjekttype_id, vegobjekttype.navn AS vt_navn, kvalitetsmåling.egenskapstype_id, egenskapstype.navn AS et_navn, område.navn AS område, kvalitetsmåling.verdi, kvalitetsmåling.dato 
                FROM kvalitetsmåling
                INNER JOIN kvalitetselement ON kvalitetsmåling.kvalitetsnivå_1 = kvalitetselement.kvalitetsnivå_1
                AND kvalitetsmåling.kvalitetsnivå_2 = kvalitetselement.kvalitetsnivå_2
                AND kvalitetsmåling.kvalitetsnivå_3 = kvalitetselement.kvalitetsnivå_3
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                INNER JOIN område ON kvalitetsmåling.område_id = område.id
                WHERE kvalitetsmåling.vegobjekttype_id = ? AND kvalitetsmåling.egenskapstype_id IS NULL
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
                (id,)   
                ).fetchall()
            kvalitetsmålinger = [{'kv':r['ke_navn'], 'vt':r['vt_navn'], 'et':r['et_navn'], 'område':r['område'], 'v':r['verdi']} for r in kvalitetsmålinger]
            referanseverdier = db.execute(
                """SELECT kvalitetselement.navn AS ke_navn, referanseverdi.vegobjekttype_id, vegobjekttype.navn AS vt_navn, referanseverdi.egenskapstype_id, egenskapstype.navn AS et_navn, område.navn AS område, referanseverdi.verdi, referanseverdi.dato 
                FROM referanseverdi
                INNER JOIN kvalitetselement ON referanseverdi.kvalitetsnivå_1 = kvalitetselement.kvalitetsnivå_1
                AND referanseverdi.kvalitetsnivå_2 = kvalitetselement.kvalitetsnivå_2
                AND referanseverdi.kvalitetsnivå_3 = kvalitetselement.kvalitetsnivå_3
                INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON referanseverdi.egenskapstype_id = egenskapstype.id
                INNER JOIN område ON referanseverdi.område_id = område.id
                WHERE referanseverdi.vegobjekttype_id = ? AND referanseverdi.egenskapstype_id IS NULL
                ORDER BY referanseverdi.vegobjekttype_id, referanseverdi.egenskapstype_id""",
                (id,)
                ).fetchall()
            referanseverdier = [{'kv':r['ke_navn'], 'vt':r['vt_navn'], 'et':r['et_navn'], 'område':r['område'], 'v':r['verdi']} for r in referanseverdier]
            kolonne1 = db.execute(
                """SELECT kvalitetselement.navn
                FROM kvalitetselement"""
            ).fetchall()
            kolonne2 = db.execute(
                """SELECT område.navn, område.fylke_id, vegsystem.vegkategori_id, vegsystem.vegnummer
                FROM område 
                LEFT JOIN vegsystem ON område.vegsystem_id = vegsystem.id"""
            ).fetchall()
            kolonne2 = [dict(row) for row in kolonne2]

            l = []
            r = []
            for kol1 in kolonne1:
                g = []
                s = []
                for kol2 in kolonne2:
                    g.append(next((r['v'] for r in kvalitetsmålinger if r['kv'] == kol1['navn'] and r['område'] == kol2['navn']),None))
                    s.append(next((r['v'] for r in referanseverdier if r['kv'] == kol1['navn'] and r['område'] == kol2['navn']),None))
                l.append(g)
                r.append(s)
            return render_template('views/datakvalitet_vegobjekttype.html', kvalitetsmålinger=l, referanseverdier=r, id=id, kolonne1=kolonne1, kolonne2=kolonne2)
        kvalitetsmålinger = db.execute(
            """SELECT vegobjekttype.id, vegobjekttype.navn
            FROM vegobjekttype"""
        ).fetchall()
        l = [(r['id'], str(r['id']) + ' - ' + r['navn']) for r in kvalitetsmålinger]
        return render_template('views/datakvalitet_vegobjekttype.html', kvalitetsmålinger=l, id=id)
    if request.method == 'POST':
        print(request.form)
        id = request.form['vegobjekttype']
        return redirect(url_for('views.datakvalitet_vegobjekttype', id=id))

@bp.route('/datakvalitet/område', methods=('GET', 'POST'))
@bp.route('/datakvalitet/område/<string:id>', methods=('GET', 'POST'))
def datakvalitet_område(id = None):
    if request.method == 'GET':
        db = get_db()
        if id is not None:
            kvalitetsmålinger = db.execute(
                """SELECT kvalitetselement.navn AS ke_navn, kvalitetsmåling.vegobjekttype_id, vegobjekttype.navn AS vt_navn, kvalitetsmåling.egenskapstype_id, egenskapstype.navn AS et_navn, område.navn AS område, kvalitetsmåling.verdi, kvalitetsmåling.dato 
                FROM kvalitetsmåling
                INNER JOIN kvalitetselement ON kvalitetsmåling.kvalitetsnivå_1 = kvalitetselement.kvalitetsnivå_1
                AND kvalitetsmåling.kvalitetsnivå_2 = kvalitetselement.kvalitetsnivå_2
                AND kvalitetsmåling.kvalitetsnivå_3 = kvalitetselement.kvalitetsnivå_3
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                INNER JOIN område ON kvalitetsmåling.område_id = område.id
                WHERE område.id = ?
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
                (id,)
                ).fetchall()
            kvalitetsmålinger = [{'kv':r['ke_navn'], 'vt':r['vt_navn'], 'et':r['et_navn'], 'område':r['område'], 'v':r['verdi']} for r in kvalitetsmålinger]
            referanseverdier = db.execute(
                """SELECT kvalitetselement.navn AS ke_navn, referanseverdi.vegobjekttype_id, vegobjekttype.navn AS vt_navn, referanseverdi.egenskapstype_id, egenskapstype.navn AS et_navn, område.navn AS område, referanseverdi.verdi, referanseverdi.dato 
                FROM referanseverdi
                INNER JOIN kvalitetselement ON referanseverdi.kvalitetsnivå_1 = kvalitetselement.kvalitetsnivå_1
                AND referanseverdi.kvalitetsnivå_2 = kvalitetselement.kvalitetsnivå_2
                AND referanseverdi.kvalitetsnivå_3 = kvalitetselement.kvalitetsnivå_3
                INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON referanseverdi.egenskapstype_id = egenskapstype.id
                INNER JOIN område ON referanseverdi.område_id = område.id
                WHERE område.id = ?
                ORDER BY referanseverdi.vegobjekttype_id, referanseverdi.egenskapstype_id""",
                (id,)
                ).fetchall()
            referanseverdier = [{'kv':r['ke_navn'], 'vt':r['vt_navn'], 'et':r['et_navn'], 'område':r['område'], 'v':r['verdi']} for r in referanseverdier]
            kolonne1 = db.execute(
                """select vegobjekttype.navn, vegobjekttype.id, null as et_navn, null as et_id
                from vegobjekttype
                union all
                select vegobjekttype.navn, vegobjekttype.id, egenskapstype.navn as et_navn, egenskapstype.id as et_id
                from vegobjekttype
                left join egenskapstype on vegobjekttype.id = egenskapstype.vegobjekttype_id
                ORDER BY vegobjekttype.id, et_id"""
            ).fetchall()
            kolonne2 = db.execute(
                """SELECT kvalitetselement.navn
                FROM kvalitetselement"""
            ).fetchall()
            kolonne1 = [dict(row) for row in kolonne1]
            kolonne2 = [dict(row) for row in kolonne2]

            l = []
            r = []
            for kol1 in kolonne1:
                #print(kol1['et_navn'], type(kol1['et_navn']))
                g = []
                s = []
                for kol2 in kolonne2:
                    g.append(next((r['v'] for r in kvalitetsmålinger if r['vt'] == kol1['navn'] and r['kv'] == kol2['navn'] and (r['et'] == kol1['et_navn'] or (r['et'] is None and kol1['et_navn'] is None))), None))
                    s.append(next((r['v'] for r in referanseverdier if r['vt'] == kol1['navn'] and r['kv'] == kol2['navn'] and (r['et'] == kol1['et_navn'] or (r['et'] is None and kol1['et_navn'] is None))),None))
                l.append(g)
                r.append(s)
            #print(l)
            return render_template('views/datakvalitet_område.html', kvalitetsmålinger=l, referanseverdier=r, id=id, kolonne1=kolonne1, kolonne2=kolonne2)
        kvalitetsmålinger = db.execute(
            """SELECT område.id, område.navn
            FROM område"""
        ).fetchall()
        l = [(r['id'], r['navn']) for r in kvalitetsmålinger]
        return render_template('views/datakvalitet_område.html', kvalitetsmålinger=l, id=id)
    if request.method == 'POST':
        id = request.form['område']
        return redirect(url_for('views.datakvalitet_område', id=id))

@bp.route('/datakvalitet/kvalitetelement', methods=('GET', 'POST'))
@bp.route('/datakvalitet/kvalitetelement/<string:id>', methods=('GET', 'POST'))
def datakvalitet_kvalitetelement(id = None):
    if request.method == 'GET':
        db = get_db()
        if id is not None:
            kv1, kv2, kv3 = id[0], id[1], id[2]
            kvalitetsmålinger = db.execute(
                """SELECT kvalitetselement.navn AS ke_navn, kvalitetsmåling.vegobjekttype_id, vegobjekttype.navn AS vt_navn, kvalitetsmåling.egenskapstype_id, egenskapstype.navn AS et_navn, område.navn AS område, kvalitetsmåling.verdi, kvalitetsmåling.dato 
                FROM kvalitetsmåling
                INNER JOIN kvalitetselement ON kvalitetsmåling.kvalitetsnivå_1 = kvalitetselement.kvalitetsnivå_1
                AND kvalitetsmåling.kvalitetsnivå_2 = kvalitetselement.kvalitetsnivå_2
                AND kvalitetsmåling.kvalitetsnivå_3 = kvalitetselement.kvalitetsnivå_3
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                INNER JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                INNER JOIN område ON kvalitetsmåling.område_id = område.id
                WHERE kvalitetselement.kvalitetsnivå_1 = ? AND kvalitetselement.kvalitetsnivå_2 = ? AND kvalitetselement.kvalitetsnivå_3 = ?""",
                (kv1, kv2, kv3)
                ).fetchall()
            kvalitetsmålinger = [{'kv':r['ke_navn'], 'vt':r['vt_navn'], 'et':r['et_navn'], 'område':r['område'], 'v':r['verdi']} for r in kvalitetsmålinger]
            print(kvalitetsmålinger)
            kolonne1 = db.execute(
                """select vegobjekttype.navn, vegobjekttype.id, null as et_navn, null as et_id
                from vegobjekttype
                union all
                select vegobjekttype.navn, vegobjekttype.id, egenskapstype.navn as et_navn, egenskapstype.id as et_id
                from vegobjekttype
                left join egenskapstype on vegobjekttype.id = egenskapstype.vegobjekttype_id
                ORDER BY vegobjekttype.id, et_id"""
            ).fetchall()
            kolonne2 = db.execute(
                """SELECT område.navn, område.fylke_id, vegsystem.vegkategori_id, vegsystem.vegnummer
                FROM område 
                LEFT JOIN vegsystem ON område.vegsystem_id = vegsystem.id"""
            ).fetchall()
            kolonne1 = [dict(row) for row in kolonne1]
            kolonne2 = [dict(row) for row in kolonne2]

            l = []
            for kol1 in kolonne1:
                g = []
                for kol2 in kolonne2:
                    g.append(next((r['v'] for r in kvalitetsmålinger if r['vt'] == kol1['navn'] and r['område'] == kol2['navn'] and r['et'] == kol1['et_navn']),None))
                l.append(g)
            return render_template('views/datakvalitet_kvalitetelement.html', kvalitetsmålinger=l, id=id, kolonne1=kolonne1, kolonne2=kolonne2)
        kvalitetsmålinger = db.execute(
            """SELECT kvalitetselement.kvalitetsnivå_1, kvalitetselement.kvalitetsnivå_2, kvalitetselement.kvalitetsnivå_3, kvalitetselement.navn
            FROM kvalitetselement"""
        ).fetchall()
        l = [(str(r['kvalitetsnivå_1']) + str(r['kvalitetsnivå_2']) + str(r['kvalitetsnivå_3']), r['navn']) for r in kvalitetsmålinger]
        return render_template('views/datakvalitet_kvalitetelement.html', kvalitetsmålinger=l, id=id)
    if request.method == 'POST':
        id = request.form['kvalitetelement']
        return redirect(url_for('views.datakvalitet_kvalitetelement', id=id))
    
@bp.route('/datakvalitet', methods=('GET', 'POST'))
@bp.route('/datakvalitet/<string:vtid>_<string:kvid>', methods=('GET', 'POST'))
def datakvalitet_kvalitetsark(vtid = None, kvid = None):
    if request.method == 'GET':
        print("dd")
        db = get_db()
        vegobjekttyper = db.execute(
            """SELECT * FROM vegobjekttype"""
        ).fetchall()
        kvalitetselementer = db.execute(
            """SELECT * FROM kvalitetselement"""
        )
        vegobjekttyper = [dict(row) for row in vegobjekttyper]
        vegobjekttyper_ = [(r['id'], str(r['id']) + ' - ' + r['navn']) for r in vegobjekttyper]
        kvalitetselementer = [dict(row) for row in kvalitetselementer]
        if vtid is not None and kvid is not None:
            print(vtid, kvid)
            egenskapstyper = db.execute(
                """SELECT * FROM egenskapstype"""
            ).fetchall()
            egenskapstyper = [dict(row) for row in egenskapstyper]
            områder = db.execute(
                """SELECT * FROM område"""
            )
            områder = [dict(row) for row in områder]
            vegobjektnavn = next((i.get('navn') for i in vegobjekttyper if i.get('id') == vtid),'Noe galt har skjedd')
            kvalitetselementnavn = next((i.get('navn') for i in kvalitetselementer if i.get('navn') == kvid), 'Noe galt har skjedd')
            kvalitetsmålinger = db.execute(
                """SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, kvalitetsmåling.område_id, kvalitetsmåling.verdi, kvalitetsmåling.dato 
                FROM kvalitetsmåling
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                WHERE kvalitetsmåling.vegobjekttype_id = ? AND kvalitetsmåling.kvalitetselement_id = ?
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
                (vtid, kvid)
                ).fetchall()
            kvalitetsmålinger = [dict(row) for row in kvalitetsmålinger]
            referanseverdier = db.execute(
                """SELECT referanseverdi.kvalitetselement_id AS kvid, referanseverdi.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, referanseverdi.område_id, referanseverdi.verdi, referanseverdi.dato 
                FROM referanseverdi
                INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
                WHERE referanseverdi.vegobjekttype_id = ? AND referanseverdi.kvalitetselement_id = ?
                ORDER BY referanseverdi.vegobjekttype_id""",
                (vtid, kvid)
                ).fetchall()
            referanseverdier = [dict(row) for row in referanseverdier]
            return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_, kvalitetselementer=kvalitetselementer, vegobjekttyper=vegobjekttyper, egenskapstyper=egenskapstyper, vtid=vtid, kvid=kvid, vegobjektnavn=vegobjektnavn, kvalitetselementnavn=kvalitetselementnavn, kvalitetsmålinger=kvalitetsmålinger, referanseverdier=referanseverdier, områder=områder)
        return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_, kvalitetselementer=kvalitetselementer)

    if request.method == 'POST':
        print("dank")
        vtid = request.form['vegobjekttyper']
        kvid = request.form['kvalitetselementer']
        return redirect(url_for('views.datakvalitet_kvalitetsark', vtid=vtid, kvid=kvid))
    
@bp.route('/kvalitetark', methods=('GET', 'POST'))
@bp.route('/kvalitetark/vegobjekttype=<string:vtid>&område=<string:omrade_id>', methods=('GET', 'POST'))
def datakvalitet_kvalitetark(vtid = None, omrade_id = None):
    if request.method == 'GET':
        db = get_db()
        vegobjekttyper = db.execute(
            """SELECT * FROM vegobjekttype"""
        ).fetchall()
        områder = db.execute(
            """SELECT * FROM område"""
        )
        vegobjekttyper = [dict(row) for row in vegobjekttyper]
        vegobjekttyper_ = [(r['id'], str(r['id']) + ' - ' + r['navn']) for r in vegobjekttyper]
        områder = [dict(row) for row in områder]
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
            områdenavn = next((i.get('navn') for i in områder if i.get('id') == omrade_id), 'Noe galt har skjedd')
            kvalitetsmålinger = db.execute(
                """SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, kvalitetsmåling.område_id, kvalitetsmåling.verdi, kvalitetsmåling.dato 
                FROM kvalitetsmåling
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                WHERE kvalitetsmåling.vegobjekttype_id = ? AND kvalitetsmåling.område_id = ?
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
                (vtid, omrade_id)
                ).fetchall()
            kvalitetsmålinger = [dict(row) for row in kvalitetsmålinger]
            kvalitetselement_relevant_ider = list(set([str(item['kvid']) for item in kvalitetsmålinger]))
            referanseverdier = db.execute(
                """SELECT referanseverdi.kvalitetselement_id AS kvid, referanseverdi.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, referanseverdi.område_id, referanseverdi.verdi, referanseverdi.dato 
                FROM referanseverdi
                INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
                WHERE referanseverdi.vegobjekttype_id = ? AND referanseverdi.område_id = ?
                ORDER BY referanseverdi.vegobjekttype_id""",
                (vtid, omrade_id)
                ).fetchall()
            referanseverdier = [dict(row) for row in referanseverdier]
            skala = db.execute(
                """SELECT * FROM skala"""
            ).fetchall()
            skala = [dict(row) for row in skala]
            return render_template('views/kvalitetark.html', vtid=vtid, omrade_id=omrade_id, vegobjekttyper_=vegobjekttyper_, vegobjekttyper=vegobjekttyper, egenskapstyper=egenskapstyper, områder=områder, kvalitetselementer=kvalitetselement, kvalitetselement_relevant_ider=kvalitetselement_relevant_ider, kvalitetsmålinger=kvalitetsmålinger, referanseverdier=referanseverdier, skala=skala)

        return render_template('views/kvalitetark.html', vegobjekttyper_=vegobjekttyper_, områder=områder)

    if request.method == 'POST':
        action = request.form['action']
        """ if action == "område2_filter":
            omrade_id2 = request.form['områder2']
            return redirect(url_for('views.datakvalitet_kvalitetark', vtid=vtid, omrade_id=omrade_id, omrade_id2=omrade_id2)) """
        print("dank")
        vtid = request.form['vegobjekttyper']
        omrade_id = request.form['områder']
        return redirect(url_for('views.datakvalitet_kvalitetark', vtid=vtid, omrade_id=omrade_id))
    
@bp.route("/add_område", methods=('GET', 'POST'))
def add_område():
    jason = request.get_json()
    vtid = jason[0]
    område_id = jason[1]
    db = get_db()
    sammenlign_kvalitetsmålinger = db.execute(
        """SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, kvalitetsmåling.område_id, kvalitetsmåling.verdi, kvalitetsmåling.dato 
        FROM kvalitetsmåling
        INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
        LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
        WHERE kvalitetsmåling.vegobjekttype_id = ? AND kvalitetsmåling.område_id = ?
        ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
        (vtid, område_id)
        ).fetchall()
    sammenlign_kvalitetsmålinger = [dict(row) for row in sammenlign_kvalitetsmålinger]
    sammenlign_referanseverdier = db.execute(
        """SELECT referanseverdi.kvalitetselement_id AS kvid, referanseverdi.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, referanseverdi.område_id, referanseverdi.verdi, referanseverdi.dato 
        FROM referanseverdi
        INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
        WHERE referanseverdi.vegobjekttype_id = ? AND referanseverdi.område_id = ?
        ORDER BY referanseverdi.vegobjekttype_id""",
        (vtid, område_id)
        ).fetchall()
    sammenlign_referanseverdier = [dict(row) for row in sammenlign_referanseverdier]
    jason_2 = {'sammenlign_kvalitetsmålinger': sammenlign_kvalitetsmålinger, 'sammenlign_referanseverdier': sammenlign_referanseverdier}
    return jason_2