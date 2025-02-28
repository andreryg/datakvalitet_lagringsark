#Egengeometri.Fullstendighet.Linjegeometri

def egengeometri_fullstendighet_linjegeometri_kvalitet(self):
    geo_linje_id = next((i['id']for i in self.egenskapstyper if i['navn'] == "Geometri, linje"), 0)
    if geo_linje_id == 0:
        return False
    
    self.df['har_linjegeometri'] = self.df['egenskaper'].apply(lambda x: 1 if geo_linje_id in [i.get('id') for i in x] else 0)
    return self.df[self.df['har_linjegeometri'] == 1].shape[0]
