from flaskr.db import get_db

def sql_filter_func(vtid, vegkategori, vegsystem_id, fylke_id, kommune_id, vegstrekning_id):
    conditions = []
    filter = [vtid]

    if vegstrekning_id != "0":
        conditions.append("RankedEntries.vegstrekning_id = ?")
        filter.append(vegstrekning_id)
    if kommune_id != "0":
        conditions.append("vegstrekning.kommune_id = ?")
        filter.append(kommune_id)
    if fylke_id != "0":
        conditions.append("vegstrekning.fylke_id = ?")
        filter.append(fylke_id)
    if vegsystem_id != "0":
        conditions.append("vegstrekning.vegsystem_id = ?")
        filter.append(vegsystem_id)
    if vegkategori != "0":
        conditions.append("vegkategori.kortnavn = ?")
        filter.append(vegkategori)

    sql_filter = " AND ".join(conditions)

    return sql_filter, filter

def hent_data(vtid, vegkategori, vegsystem_id, fylke_id, kommune_id, vegstrekning_id):
    """
    Henter data fra database.
    """
    sql_filter, filter = sql_filter_func(vtid, vegkategori, vegsystem_id, fylke_id, kommune_id, vegstrekning_id)

    db = get_db()
    kvalitetsmålinger = db.execute(
        f"""WITH RankedEntries AS (
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY kvalitetselement_id, vegobjekttype_id, egenskapstype_id, vegstrekning_id ORDER BY dato DESC) AS rank
            FROM
                kvalitetsmåling
        )
        SELECT RankedEntries.kvalitetselement_id AS kvid, RankedEntries.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, RankedEntries.egenskapstype_id as etid, egenskapstype.navn AS etnavn, SUM(RankedEntries.verdi) as verdi, SUM(RankedEntries.ref_verdi) as ref_verdi{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
        FROM RankedEntries
        INNER JOIN vegobjekttype ON RankedEntries.vegobjekttype_id = vegobjekttype.id
        LEFT JOIN egenskapstype ON RankedEntries.egenskapstype_id = egenskapstype.id
        join vegstrekning on RankedEntries.vegstrekning_id = vegstrekning.id
        left join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
        left join vegkategori on vegsystem.vegkategori_id = vegkategori.id
        WHERE RankedEntries.vegobjekttype_id = ? AND RankedEntries.rank = 1 {"AND "+sql_filter if sql_filter else ""}
        GROUP BY RankedEntries.kvalitetselement_id, RankedEntries.vegobjekttype_id, vegobjekttype.navn, RankedEntries.egenskapstype_id, egenskapstype.navn{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
        ORDER BY RankedEntries.vegobjekttype_id, RankedEntries.egenskapstype_id""",
        filter
        ).fetchall()
    kvalitetsmålinger = [dict(row) for row in kvalitetsmålinger]

    kvalitetsmålinger_forrige = db.execute(
        f"""WITH RankedEntries AS (
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY kvalitetselement_id, vegobjekttype_id, egenskapstype_id, vegstrekning_id ORDER BY dato DESC) AS rank
            FROM
                kvalitetsmåling
        )
        SELECT RankedEntries.kvalitetselement_id AS kvid, RankedEntries.vegobjekttype_id as vtid, vegobjekttype.navn AS vtnavn, RankedEntries.egenskapstype_id as etid, egenskapstype.navn AS etnavn, SUM(RankedEntries.verdi) as verdi, SUM(RankedEntries.ref_verdi) as ref_verdi{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
        FROM RankedEntries
        INNER JOIN vegobjekttype ON RankedEntries.vegobjekttype_id = vegobjekttype.id
        LEFT JOIN egenskapstype ON RankedEntries.egenskapstype_id = egenskapstype.id
        join vegstrekning on RankedEntries.vegstrekning_id = vegstrekning.id
        left join vegsystem on vegstrekning.vegsystem_id = vegsystem.id
        left join vegkategori on vegsystem.vegkategori_id = vegkategori.id
        WHERE RankedEntries.vegobjekttype_id = ? AND RankedEntries.rank = 2 {"AND "+sql_filter if sql_filter else ""}
        GROUP BY RankedEntries.kvalitetselement_id, RankedEntries.vegobjekttype_id, vegobjekttype.navn, RankedEntries.egenskapstype_id, egenskapstype.navn{", "+sql_filter.replace(" = ?", "").replace(" AND ", ", ") if sql_filter else ""}
        ORDER BY RankedEntries.vegobjekttype_id, RankedEntries.egenskapstype_id""",
        filter
        ).fetchall()
    kvalitetsmålinger_forrige = [dict(row) for row in kvalitetsmålinger_forrige]

    for row in kvalitetsmålinger:
        row['verdi_forrige'] = next((item['verdi'] for item in kvalitetsmålinger_forrige if item['kvid'] == row['kvid'] and item['vtid'] == row['vtid'] and (item['etid'] is None or item['etid'] == row['etid'])), None)
        row['ref_verdi_forrige'] = next((item['ref_verdi'] for item in kvalitetsmålinger_forrige if item['kvid'] == row['kvid'] and item['vtid'] == row['vtid']), None)

    #print(kvalitetsmålinger)
    return kvalitetsmålinger