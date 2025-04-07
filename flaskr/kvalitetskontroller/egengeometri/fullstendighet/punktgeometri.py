#Egengeometri.Fullstendighet.Punktgeometri

def egengeometri_fullstendighet_punktgeometri_kvalitet(df, egenskapstyper):
    geo_punkt_id = next((i.get('id')for i in egenskapstyper if i.get('navn') == "Geometri, punkt"), 0)
    if geo_punkt_id == 0:
        return False
    
    df['har_punktgeometri'] = df['egenskaper'].apply(lambda x: 1 if geo_punkt_id in [i.get('id') for i in x] else 0)
    return df[df['har_punktgeometri'] == 1].shape[0], df.shape[0]