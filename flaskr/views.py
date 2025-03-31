from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from flaskr.db import get_db
from flaskr.aggregering import aggreger_vegstrekninger
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
        if vegobjekttype['vt_id'] == 3:
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
            if omrade_id != "0":
                if kommune_id != "0":
                    sql_filter = "kvalitetsmåling.vegstrekning_id = ? AND vegstrekning.kommune_id = ?"
                    filter = (vtid, omrade_id, kommune_id,)
                elif fylke_id != "0":
                    sql_filter = "kvalitetsmåling.vegstrekning_id = ? AND vegstrekning.fylke_id = ?"
                    filter = (vtid, omrade_id, fylke_id,)
                else:
                    sql_filter = "kvalitetsmåling.vegstrekning_id = ?"
                    filter = (vtid, omrade_id,)
            elif kommune_id != "0":
                if vegsystem_id:
                    sql_filter = "vegstrekning.kommune_id = ? AND vegstrekning.vegsystem_id = ?"
                    filter = (vtid, kommune_id, vegsystem_id,)
                elif vegkategori != "0":
                    sql_filter = "vegstrekning.kommune_id = ? AND vegkategori.kortnavn = ?"
                    filter = (vtid, kommune_id, vegkategori,)
                else:
                    sql_filter = "vegstrekning.kommune_id = ?"
                    filter = (vtid, kommune_id,)
            elif fylke_id != "0":
                if vegsystem_id != "0":
                    sql_filter = "vegstrekning.fylke_id = ? AND vegstrekning.vegsystem_id = ?"
                    filter = (vtid, fylke_id, vegsystem_id,)
                elif vegkategori != "0":
                    sql_filter = "vegstrekning.fylke_id = ? AND vegkategori.kortnavn = ?"
                    filter = (vtid, fylke_id, vegkategori,)
                else:
                    sql_filter = "vegstrekning.fylke_id = ?"
                    filter = (vtid, fylke_id,)
            elif vegsystem_id != "0":
                sql_filter = "vegstrekning.vegsystem_id = ?"
                filter = (vtid, vegsystem_id,)
            elif vegkategori != "0":
                sql_filter = "vegkategori.kortnavn = ?"
                filter = (vtid, vegkategori,)
            else:
                sql_filter = ""
                filter = (vtid,)

            if omrade_id != "0":
                område_navn = db.execute(
                    """SELECT navn FROM vegstrekning WHERE id = ?""",
                    (omrade_id,)
                ).fetchone()[0]
            else:
                område_navn = ""
            if vegkategori != "0":
                vegkategori_navn = db.execute(
                    """SELECT navn FROM vegkategori WHERE kortnavn = ?""",
                    (vegkategori,)
                ).fetchone()[0]
            else:    
                vegkategori_navn = ""
            if vegsystem_id != "0":
                vegsystem_navn = db.execute(
                    """SELECT vegnummer FROM vegsystem WHERE id = ?""",
                    (vegsystem_id,)
                ).fetchone()[0]
            else:
                vegsystem_navn = ""
            if fylke_id != "0":
                fylke_navn = db.execute(
                    """SELECT navn FROM fylke WHERE id = ?""",
                    (fylke_id,)
                ).fetchone()[0]
            else:
                fylke_navn = ""
            if kommune_id != "0":
                kommune_navn = db.execute(
                    """SELECT navn FROM kommune WHERE id = ?""",
                    (kommune_id,)
                ).fetchone()[0]
            else:
                kommune_navn = ""
            område_navn = vegkategori_navn + " " + vegsystem_navn + " " + fylke_navn + " " + kommune_navn + " " + område_navn
            område_navn = " ".join(område_navn.split())

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
            kv = f"""SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, SUM(kvalitetsmåling.verdi) as verdi{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
                FROM kvalitetsmåling
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                join vegstrekning on kvalitetsmåling.vegstrekning_id = vegstrekning.id
                left join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
                left join vegkategori on vegsystem.vegkategori_id = vegkategori.id
                WHERE kvalitetsmåling.vegobjekttype_id = ? {"AND "+sql_filter if sql_filter else ""}
                GROUP BY kvalitetsmåling.kvalitetselement_id, kvalitetsmåling.vegobjekttype_id, vegobjekttype.navn, kvalitetsmåling.egenskapstype_id, egenskapstype.navn{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id"""
            #print(kv)
            print(filter)
            kvalitetsmålinger = db.execute(
                f"""SELECT kvalitetsmåling.kvalitetselement_id AS kvid, kvalitetsmåling.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, kvalitetsmåling.egenskapstype_id as etid, egenskapstype.navn AS etnavn, SUM(kvalitetsmåling.verdi) as verdi{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
                FROM kvalitetsmåling
                INNER JOIN vegobjekttype ON kvalitetsmåling.vegobjekttype_id = vegobjekttype.id
                LEFT JOIN egenskapstype ON kvalitetsmåling.egenskapstype_id = egenskapstype.id
                join vegstrekning on kvalitetsmåling.vegstrekning_id = vegstrekning.id
                left join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
                left join vegkategori on vegsystem.vegkategori_id = vegkategori.id
                WHERE kvalitetsmåling.vegobjekttype_id = ? {"AND "+sql_filter if sql_filter else ""}
                GROUP BY kvalitetsmåling.kvalitetselement_id, kvalitetsmåling.vegobjekttype_id, vegobjekttype.navn, kvalitetsmåling.egenskapstype_id, egenskapstype.navn{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
                ORDER BY kvalitetsmåling.vegobjekttype_id, kvalitetsmåling.egenskapstype_id""",
                filter
                ).fetchall()
            kvalitetsmålinger = [dict(row) for row in kvalitetsmålinger]
            kvalitetselement_relevant_ider = list(set([str(item['kvid']) for item in kvalitetsmålinger]))
            referanseverdier = db.execute(
                f"""SELECT referanseverdi.kvalitetselement_id AS kvid, referanseverdi.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, SUM(referanseverdi.verdi) as verdi{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ").replace("kvalitetsmåling", "referanseverdi") if sql_filter else ""}
                FROM referanseverdi
                INNER JOIN vegobjekttype ON referanseverdi.vegobjekttype_id = vegobjekttype.id
                join vegstrekning on referanseverdi.vegstrekning_id = vegstrekning.id
                left join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
                left join vegkategori on vegsystem.vegkategori_id = vegkategori.id
                WHERE referanseverdi.vegobjekttype_id = ? {"AND "+sql_filter.replace("kvalitetsmåling", "referanseverdi") if sql_filter else ""}
                GROUP BY referanseverdi.kvalitetselement_id, referanseverdi.vegobjekttype_id, vegobjekttype.navn{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ").replace("kvalitetsmåling", "referanseverdi") if sql_filter else ""}
                ORDER BY referanseverdi.vegobjekttype_id""",
                filter
                ).fetchall()
            referanseverdier = [dict(row) for row in referanseverdier]
            skala = db.execute(
                """SELECT * FROM skala"""
            ).fetchall()
            skala = [dict(row) for row in skala]
            print(kvalitetsmålinger, referanseverdier)
            return render_template('views/kvalitetark.html', vtid=vtid, omrade_id=omrade_id, vegobjekttyper_=vegobjekttyper_, vegobjekttyper=vegobjekttyper, egenskapstyper=egenskapstyper, områder=vegstrekninger, kvalitetselementer=kvalitetselement, kvalitetselement_relevant_ider=kvalitetselement_relevant_ider, kvalitetsmålinger=kvalitetsmålinger, referanseverdier=referanseverdier, skala=skala, vegkategorier=vegkategorier, vegsystemer=vegsystemer, fylker=fylker, kommuner=kommuner, område_navn=område_navn)

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