#Relasjoner.Fullstendighet.Datterobjekt
import numpy as np

def relasjoner_fullstendighet_datterobjekt_kvalitet(df, egenskapstyper):
    df['har_relasjon'] = np.where(df[['barn']].isna().all(axis=1), 0, 1)
    return df[df['har_relasjon'] == 1].shape[0], df.shape[0]