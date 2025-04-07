#Egengeometri.Fullstendighet.Generell

def egengeometri_fullstendighet_generell_kvalitet(df, egenskapstyper):
    geo_linje_ids = [i.get('id') for i in egenskapstyper if "Geometri" in i.get('navn')]
    if not geo_linje_ids:
        return False
    
    df['har_geometri'] = df['egenskaper'].apply(lambda x: 1 if any(geo_id in [i.get('id') for i in x] for geo_id in geo_linje_ids) else 0)
    return df[df['har_geometri'] == 1].shape[0], df.shape[0]