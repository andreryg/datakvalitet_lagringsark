from flaskr.db import get_db

def generer_label(omrade_id, vegkategori, vegsystem_id, fylke_id, kommune_id):
    db = get_db()
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
    print(område_navn, vegkategori_navn, vegsystem_navn, fylke_navn, kommune_navn)
    område_navn = vegkategori_navn + " " + str(vegsystem_navn) + " " + fylke_navn + " " + kommune_navn + " " + område_navn
    område_navn = " ".join(område_navn.split())
    if område_navn == "":
        område_navn = "Norge"

    return område_navn