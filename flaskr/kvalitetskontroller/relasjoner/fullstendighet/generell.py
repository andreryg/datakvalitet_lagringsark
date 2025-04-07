#Relasjoner.Fullstendighet.Generell
import numpy as np

def relasjoner_fullstendighet_generell_kvalitet(df, egenskapstyper):
    df['har_relasjon'] = np.where(df[['barn', 'foreldre']].isna().all(axis=1), 0, 1)
    return df[df['har_relasjon'] == 1].shape[0], df.shape[0]