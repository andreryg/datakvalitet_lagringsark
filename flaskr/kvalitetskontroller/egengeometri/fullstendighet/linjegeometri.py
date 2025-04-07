#Egengeometri.Fullstendighet.Linjegeometri

def egengeometri_fullstendighet_linjegeometri_kvalitet(df, egenskapstyper):
    geo_linje_id = next((i.get('id')for i in egenskapstyper if i.get('navn') == "Geometri, linje"), 0)
    if geo_linje_id == 0:
        return False
    
    df['har_linjegeometri'] = df['egenskaper'].apply(lambda x: 1 if geo_linje_id in [i.get('id') for i in x] else 0)
    return df[df['har_linjegeometri'] == 1].shape[0], df.shape[0]