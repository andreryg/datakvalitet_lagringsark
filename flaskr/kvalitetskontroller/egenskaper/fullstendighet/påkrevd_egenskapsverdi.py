#Egenskaper.Fullstendighet.Påkrevd_egenskapsverdi

def egenskaper_fullstendighet_påkrevd_egenskapsverdi_kvalitet(df, egenskapstyper):
    påkrevd_ids = [i.get('id') for i in egenskapstyper if "PÅKREVD" in i.get('viktighet')]
    if not påkrevd_ids:
        return False
    kvalitet = {}
    for påkrevd_id in påkrevd_ids:
        df['har_egenskapstype'] = df['egenskaper'].apply(lambda x: 1 if påkrevd_id in [i.get('id') for i in x] else 0)
        kvalitet[påkrevd_id] = df[df['har_egenskapstype'] == 1].shape[0]
    return kvalitet