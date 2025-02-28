import pandas as pd

def main():
    kommuner_df = pd.read_csv("flaskr/Kommune_946-eksport.csv", sep=";", encoding="utf-8")
    kommuner_df = kommuner_df[['EGS.KOMMUNENUMMER.11769', 'EGS.KOMMUNENAVN.11770']]
    kommuner_df = kommuner_df.rename(columns={"EGS.KOMMUNENUMMER.11769": "id", "EGS.KOMMUNENAVN.11770": "navn"})
    kommuner_df = kommuner_df[pd.notna(kommuner_df['id'])]
    kommuner_df['fylke_id'] = kommuner_df.apply(lambda x: int(str(x['id'])[:2]), axis=1)
    kommuner_df.to_excel("flaskr/kommuner.xlsx", index=False)

if __name__ == "__main__":
    main()