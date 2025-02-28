# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 12:11:16 2024

@author: andryg
"""

import sqlite3
import datetime
import click
from flask import current_app, g
import pandas as pd

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
            )
        g.db.row_factory = sqlite3.Row
    
    return g.db

def close_db(e = None):
    db = g.pop('db', None)
    
    if db is not None:
        db.close()

def fyll_inn_tabeller():
    db = get_db()
    vegstrekninger_df = pd.read_excel("flaskr/alle_verstrekninger.xlsx")
    test_result = db.execute("SELECT * FROM vegkategori limit 1")
    if not test_result.fetchone():
        print("Fyller inn vegkategori")
        file = open("flaskr/vegkategorier.txt", "r", encoding="utf-8")
        vegkategorier = [tuple([None if i == "0" else i for i in line.replace("\n","").split("; ")]) for line in file.readlines()]
        db.executemany(
            "INSERT INTO vegkategori (navn, kortnavn) VALUES (?, ?)",
            vegkategorier
            )

    test_result = db.execute("SELECT * FROM vegsystem limit 1")
    if not test_result.fetchone():
        print("Fyller inn vegsystem")
        df = vegstrekninger_df[['vegkategori', 'vegfase', 'vegnummer']]
        df['vegkategori_id'] = df['vegkategori'].apply(lambda x: 1 if x == "E" else 2 if x == "R" else 3 if x == "F" else 4 if x == "K" else 0)
        df = df[['vegkategori_id', 'vegfase', 'vegnummer']]
        df = df.drop_duplicates()
        db.executemany(
            "INSERT INTO vegsystem (vegkategori_id, fase, vegnummer) VALUES (?, ?, ?)",
            df.values.tolist()
            )

    test_result = db.execute("SELECT * FROM fylke limit 1")
    if not test_result.fetchone():
        print("Fyller inn fylke")
        file = open("flaskr/fylker.txt", "r", encoding="utf-8")
        fylker = [tuple([None if i == "0" else i for i in line.replace("\n","").split("; ")]) for line in file.readlines()]
        db.executemany(
            "INSERT INTO fylke (id, navn) VALUES (?, ?)",
            fylker
            )
        
    test_result = db.execute("SELECT * FROM kvalitetsnivå_1 limit 1")
    if not test_result.fetchone():
        print("Fyller inn kvalitetsnivå_1")
        file = open("flaskr/kvalitetsnivå_1.txt", "r", encoding="utf-8")
        kvalitetsnivå_1 = [tuple([None if i == "0" else i for i in line.replace("\n","").split("; ")]) for line in file.readlines()]
        db.executemany(
            "INSERT INTO kvalitetsnivå_1 (navn) VALUES (?)",
            kvalitetsnivå_1
            )
        
    test_result = db.execute("SELECT * FROM kvalitetsnivå_2 limit 1")
    if not test_result.fetchone():
        print("Fyller inn kvalitetsnivå_2")
        file = open("flaskr/kvalitetsnivå_2.txt", "r", encoding="utf-8")
        kvalitetsnivå_2 = [tuple([None if i == "0" else i for i in line.replace("\n","").split("; ")]) for line in file.readlines()]
        db.executemany(
            "INSERT INTO kvalitetsnivå_2 (navn) VALUES (?)",
            kvalitetsnivå_2
            )

    test_result = db.execute("SELECT * FROM kvalitetselement limit 1")
    if not test_result.fetchone():
        print("Fyller inn kvalitetselement")
        file = open("flaskr/kvalitetselementer.txt", "r", encoding="utf-8")
        kvalitetselementer = [tuple([None if i == "0" else i for i in line.replace("\n","").split("; ")]) for line in file.readlines()]
        db.executemany(
            "INSERT INTO kvalitetselement (navn, kvalitetsnivå_1, kvalitetsnivå_2, kvalitetsnivå_3) VALUES (?, ?, ?, ?)",
            kvalitetselementer
            )
        
    test_result = db.execute("SELECT * FROM skala limit 1")
    if not test_result.fetchone():
        print("Fyller inn skala")
        file = open("flaskr/skala.txt", "r", encoding="utf-8")
        skala = [tuple([None if i == "0" else i for i in line.replace("\n","").split("; ")]) for line in file.readlines()]
        db.executemany(
            "INSERT INTO skala (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, sep_1, sep_2, sep_3, sep_4) VALUES (?, ?, ?, ?, ?, ?, ?)",
            skala
            )
        
    test_result = db.execute("SELECT * FROM vegstrekning limit 1")
    if not test_result.fetchone():
        vegstrekninger_df['vegsystem_id'] = vegstrekninger_df.apply(lambda x: db.execute("SELECT id FROM vegsystem WHERE vegkategori_id = ? AND fase = ? AND vegnummer = ?", (1 if x['vegkategori'] == "E" else 2 if x['vegkategori'] == "R" else 3 if x['vegkategori'] == "F" else 4 if x['vegkategori'] == "K" else 0, x['vegfase'], x['vegnummer'])).fetchone()[0], axis=1)
        vegstrekninger_df['navn'] = vegstrekninger_df.apply(lambda x: f"{x['vegsystem']} {x['strekning']}", axis=1)
        db.executemany(
            "INSERT INTO vegstrekning (vegsystem_id, navn) VALUES (?, ?)",
            vegstrekninger_df[['vegsystem_id', 'navn']].values.tolist()
            )

    db.commit()
        
def init_db():
    db = get_db()
    
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
        
@click.command('init-db')
def init_db_command():
    init_db()
    fyll_inn_tabeller()
    click.echo('Initialized the database.')
    
sqlite3.register_converter("timestamp", lambda x: datetime.datetime.fromisoformat(x.decode()))

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)