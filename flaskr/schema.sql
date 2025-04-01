DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS vegkategori;
DROP TABLE IF EXISTS vegsystem;
DROP TABLE IF EXISTS vegstrekning;
DROP TABLE IF EXISTS kvalitetsnivå_1;
DROP TABLE IF EXISTS kvalitetsnivå_2;
DROP TABLE IF EXISTS kvalitetselement;
DROP TABLE IF EXISTS vegobjekttype;
DROP TABLE IF EXISTS egenskapstype;
DROP TABLE IF EXISTS kvalitetsmåling;
DROP TABLE IF EXISTS referanseverdi;
DROP TABLE IF EXISTS fylke;
DROP TABLE IF EXISTS kommune;
DROP TABLE IF EXISTS skala;
DROP TABLE IF EXISTS kopl_område;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE vegkategori (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL,
    kortnavn CHARACTER(1) NOT NULL
);

CREATE TABLE vegsystem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vegkategori_id INTEGER NOT NULL,
    fase CHARACTER(1),
    vegnummer INTEGER,
    FOREIGN KEY (vegkategori_id) REFERENCES vegkategori (id)
);

CREATE TABLE kvalitetsnivå_1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL
);

CREATE TABLE kvalitetsnivå_2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL
);

CREATE TABLE kvalitetselement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL,
    kvalitetsnivå_1 INTEGER NOT NULL,
    kvalitetsnivå_2 INTEGER NOT NULL,
    kvalitetsnivå_3 INTEGER NOT NULL,
    FOREIGN KEY (kvalitetsnivå_1) REFERENCES kvalitetsnivå_1 (id),
    FOREIGN KEY (kvalitetsnivå_2) REFERENCES kvalitetsnivå_2 (id)
);

CREATE TABLE vegobjekttype (
    id INTEGER PRIMARY KEY,
    navn TEXT NOT NULL,
    hovedkategori TEXT NOT NULL
);

CREATE TABLE egenskapstype (
    id INTEGER PRIMARY KEY,
    navn TEXT NOT NULL,
    vegobjekttype_id INTEGER NOT NULL,
    datatype TEXT,
    viktighet TEXT,
    FOREIGN KEY (vegobjekttype_id) REFERENCES vegobjekttype (id)
);

CREATE TABLE fylke (
    id INTEGER PRIMARY KEY,
    navn TEXT NOT NULL
);

CREATE TABLE kommune (
    id INTEGER PRIMARY KEY,
    navn TEXT NOT NULL,
    fylke_id INTEGER NOT NULL,
    FOREIGN KEY (fylke_id) REFERENCES fylke (id)
);

CREATE TABLE vegstrekning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vegsystem_id INTEGER NOT NULL,
    vegstrekning TEXT,
    navn TEXT NOT NULL,
    fylke_id INTEGER,
    kommune_id INTEGER,
    FOREIGN KEY (vegsystem_id) REFERENCES vegsystem (id),
    FOREIGN KEY (fylke_id) REFERENCES fylke (id),
    FOREIGN KEY (kommune_id) REFERENCES kommune (id)
);

CREATE TABLE kvalitetsmåling (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kvalitetselement_id INTEGER NOT NULL,
    vegobjekttype_id INTEGER NOT NULL,
    egenskapstype_id INTEGER,
    verdi INTEGER NOT NULL,
    ref_verdi INTEGER NOT NULL,
    dato TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    vegstrekning_id INTEGER NOT NULL,
    FOREIGN KEY (kvalitetselement_id) REFERENCES kvalitetselement (id),
    FOREIGN KEY (vegobjekttype_id) REFERENCES vegobjekttype (id),
    FOREIGN KEY (egenskapstype_id) REFERENCES egenskapstype (id),
    FOREIGN KEY (vegstrekning_id) REFERENCES vegstrekning (id)
);

CREATE TABLE skala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kvalitetselement_id INTEGER,
    vegobjekttype_id INTEGER,
    egenskapstype_id INTEGER,
    sep_1 INTEGER NOT NULL,
    sep_2 INTEGER NOT NULL,
    sep_3 INTEGER NOT NULL,
    sep_4 INTEGER NOT NULL,
    FOREIGN KEY (kvalitetselement_id) REFERENCES kvalitetselement (id),
    FOREIGN KEY (vegobjekttype_id) REFERENCES vegobjekttype (id),
    FOREIGN KEY (egenskapstype_id) REFERENCES egenskapstype (id)
);