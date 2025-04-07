#Egenskaper.Fullstendighet.Generell

def egenskaper_fullstendighet_generell_kvalitet(df, egenskapstyper):
    kvalitet = {}
    for egenskapstype in egenskapstyper:
        df['har_egenskapstype'] = df['egenskaper'].apply(lambda x: 1 if egenskapstype.get('id') in [i.get('id') for i in x] else 0)
        kvalitet[egenskapstype.get('id')] = df[df['har_egenskapstype'] == 1].shape[0]
    return kvalitet, df.shape[0]