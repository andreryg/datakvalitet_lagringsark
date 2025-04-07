#Relasjoner.Fullstendighet.Morobjekt
import numpy as np

def relasjoner_fullstendighet_morobjekt_kvalitet(df, egenskapstyper):
    df['har_relasjon'] = np.where(df[['foreldre']].isna().all(axis=1), 0, 1)
    return df[df['har_relasjon'] == 1].shape[0], df.shape[0]