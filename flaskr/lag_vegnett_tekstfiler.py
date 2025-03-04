import pandas as pd


def main():
    df = pd.read_csv("flaskr/vegnett.csv", sep=";", encoding="utf-8")
    df = df[['VSR.VEGSYSTEMREFERANSE', 'LOK.FYLKE-ID', 'LOK.KOMMUNE-ID']]
    df = df[pd.notna(df['VSR.VEGSYSTEMREFERANSE'])]
    df['strekning'] = df['VSR.VEGSYSTEMREFERANSE'].apply(lambda x: x.split()[1].split("D")[0])
    df['VSR.VEGSYSTEMREFERANSE'] = df['VSR.VEGSYSTEMREFERANSE'].apply(lambda x: x.split()[0])
    df['vegkategori'] = df['VSR.VEGSYSTEMREFERANSE'].apply(lambda x: x[0])
    df = df[df['vegkategori'].isin(['E', 'R', 'F', 'K'])] #Midlertidig løsning
    df['vegfase'] = df['VSR.VEGSYSTEMREFERANSE'].apply(lambda x: x[1])
    df['vegnummer'] = df['VSR.VEGSYSTEMREFERANSE'].apply(lambda x: int(x[2:]))
    df = df.rename(columns={"VSR.VEGSYSTEMREFERANSE": "vegsystem", "LOK.FYLKE-ID": "fylke_id", "LOK.KOMMUNE-ID": "kommune_id"})
    df['kommune_id'] = df.apply(lambda x: x['kommune_id'] if x['vegkategori'] == 'K' else 0, axis=1)
    df['fylke_id'] = df.apply(lambda x: x['fylke_id'] if x['vegkategori'] in ['K', 'F', 'E', 'R'] else 0, axis=1)
    print(df.shape)
    df = df.drop_duplicates()
    print(df.shape)
    df = df[df['vegfase'] == "V"]
    print(df.shape)
    print(df.head())
    df.to_excel("flaskr/alle_vegstrekninger.xlsx", index=False)

if __name__ == "__main__":
    main()