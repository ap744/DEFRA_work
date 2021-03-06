# This code compare GEOS-Chem model and DEFRA sites sulphate 
# Please contact Alok Pandey ap744@leicester.ac.uk for any further clarifications or details

#import libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os 
from sklearn.preprocessing import StandardScaler
import datetime
import xarray as xr
import cartopy.crs as ccrs
from cartopy.io.shapereader import Reader
from cartopy.feature import ShapelyFeature
import matplotlib.cm as cm
import glob
from scipy import stats
#from bootstrap import rma
from scipy.stats import gaussian_kde

#Use todays date to plot files - good practice to save files name with date
Today_date=datetime.datetime.now().strftime("%Y%m%d")

###Different cmap options
# cmap = matplotlib.cm.get_cmap('brewer_RdBu_11')
# cmap = cm.jet
cmap = cm.rainbow
#cmap = cm.YlOrRd

#read UKEAP sulphate datasets here scratch_alok -> /scratch/uptrop/ap744
path='/scratch/uptrop/ap744/UKEAP_data/UKEAP_AcidGases_Aerosol/UKEAP_Particulate_Sulphate/'
sulphate_files=glob.glob(path + '28-UKA0*-2016_particulate_sulphate_*.csv')
print (sulphate_files)

# read csv file having DEFRA sites details
sites = pd.read_csv('/scratch/uptrop/ap744/UKEAP_data/DEFRA_UKEAP_sites_details/UKEAP_AcidGases_Aerosol_sites_details.csv', encoding= 'unicode_escape')
#print (sites.head(10))
ID = sites["UK-AIR_ID"]
print (ID)

# site wise annual mean computation  
x = []
for f in sulphate_files:
	df = pd.read_csv(f,parse_dates=["Start Date", "End Date"])  
	print (df.head(5))
	print (len(sulphate_files))
	sitesA = sites.copy()
	#df['Measurement'].values[df['Measurement'] <=0.1] = np.nan

	#Annual Mean calculation
	mean_A= df["Measurement"].mean() # to compute annual mean
	print (mean_A, f[87:95])
	
	#MAMJJAS mean Calculation
	msp_start = pd.to_datetime("15/02/2016")
	msp_end = pd.to_datetime("15/10/2016")
	msp_subset = df[(df["Start Date"] > msp_start) & (df["End Date"] < msp_end)]
	mean_msp = msp_subset["Measurement"].mean()
	
	#MAM mean Calculation
	mam_start = pd.to_datetime("15/02/2016")
	mam_end = pd.to_datetime("15/06/2016")
	mam_subset = df[(df["Start Date"] > mam_start) & (df["End Date"] < mam_end)]
	mean_mam = mam_subset["Measurement"].mean()
	
	#JJA mean Calculation
	jja_start = pd.to_datetime("15/05/2016")
	jja_end = pd.to_datetime("15/09/2016")
	jja_subset = df[(df["Start Date"] > jja_start) & (df["End Date"] < jja_end)]
	mean_jja = jja_subset["Measurement"].mean()

	#SON mean Calculation
	son_start = pd.to_datetime("15/08/2016")
	son_end = pd.to_datetime("15/11/2016")
	son_subset = df[(df["Start Date"] > son_start) & (df["End Date"] < son_end)]
	mean_son = son_subset["Measurement"].mean()
	
	#DJF mean Calculation
	
	d_start = pd.to_datetime("15/11/2016")
	d_end = pd.to_datetime("31/12/2016")
	d_subset = df[(df["Start Date"] > d_start) & (df["End Date"] < d_end)]
	mean_d = d_subset["Measurement"].mean()
	print (mean_d, 'mean_d')
	
	
	jf_start = pd.to_datetime("01/01/2016")
	jf_end = pd.to_datetime("15/03/2016")
	jf_subset = df[(df["Start Date"] > jf_start) & (df["End Date"] < jf_end)]
	mean_jf = jf_subset["Measurement"].mean()
	print (mean_jf, 'mean_jf')
	
	
	mean_djf_a  = np.array([mean_d, mean_jf])
	
	mean_djf = np.nanmean(mean_djf_a, axis=0)
	print (mean_djf, 'mean_djf')
	
	sitesA["sulphate_annual_mean"] = mean_A
	sitesA["sulphate_msp_mean"] = mean_msp
	sitesA["sulphate_mam_mean"] = mean_mam
	sitesA["sulphate_jja_mean"] = mean_jja
	sitesA["sulphate_son_mean"] = mean_son
	sitesA["sulphate_djf_mean"] = mean_djf
	#print (sitesA.head(10))
	
	x.append(
	{
		'UK-AIR_ID':f[87:95],
		'sulphate_annual_mean':mean_A,
		'sulphate_msp_mean':mean_msp,
		'sulphate_mam_mean':mean_mam,
		'sulphate_jja_mean':mean_jja,
		'sulphate_son_mean':mean_son,
		'sulphate_djf_mean':mean_djf
		}
		)
	#print (x)
	
id_mean = pd.DataFrame(x)
#print (id_mean.head(3))

df_merge_col = pd.merge(sites, id_mean, on='UK-AIR_ID', how ='right')
print (df_merge_col.head(25))

#####export csv file having site wise annual mean information if needed 
#df_merge_col.to_csv(r'/home/a/ap744/scratch_alok/python_work/sulphate_annual_mean.csv')

#drop extra information from pandas dataframe
df_merge_colA = df_merge_col.drop(['S No','2016_Data'], axis=1)
print (df_merge_colA.head(5))
df_merge_colB = df_merge_colA.copy()

###################################################################################
###########  Delete Data over Scotland           ##################################
###################################################################################
df_merge_colB.drop(df_merge_colB[df_merge_colB['Lat'] > 56].index, inplace = True) 
print(df_merge_colB.head(11)) 
df_merge_colB.reset_index(drop=True, inplace=True)
print(df_merge_colB.head(11)) 


# change datatype to float to remove any further problems
df_merge_colA['Long'] = df_merge_colA['Long'].astype(float)
df_merge_colA['Lat'] = df_merge_colA['Lat'].astype(float)
df_merge_colB['Long'] = df_merge_colB['Long'].astype(float)
df_merge_colB['Lat'] = df_merge_colB['Lat'].astype(float)

#get sites information
sites_lon = df_merge_colA['Long']
sites_lat = df_merge_colA['Lat']


#get sites information for calculation
sites_lon_c = df_merge_colB['Long']
sites_lat_c = df_merge_colB['Lat']

#getting annual mean data
sites_sulphate_AM = df_merge_colA['sulphate_annual_mean']
#seasonal mean data
sites_sulphate_msp = df_merge_colA['sulphate_msp_mean']
sites_sulphate_mam = df_merge_colA['sulphate_mam_mean']
sites_sulphate_jja = df_merge_colA['sulphate_jja_mean']
sites_sulphate_son = df_merge_colA['sulphate_son_mean']
sites_sulphate_djf = df_merge_colA['sulphate_djf_mean']
sites_name = df_merge_colA['Site_Name']
print (sites_sulphate_AM, sites_name, sites_lat, sites_lon)


#seasonal mean data for calculation
sites_sulphate_AM_c = df_merge_colB['sulphate_annual_mean']
sites_sulphate_msp_c = df_merge_colB['sulphate_msp_mean']
sites_sulphate_mam_c = df_merge_colB['sulphate_mam_mean']
sites_sulphate_jja_c = df_merge_colB['sulphate_jja_mean']
sites_sulphate_son_c = df_merge_colB['sulphate_son_mean']
sites_sulphate_djf_c = df_merge_colB['sulphate_djf_mean']
sites_name_c = df_merge_colB['Site_Name']



##############  new to read files  #############
#####Reading GEOS-Chem files ################
path_AerosolMass_2 = "/data/uptrop/Projects/DEFRA-NH3/GC/geosfp_eu_naei_iccw/AerosolMass/2016/"

########################### 50% increase in NH3 Emission ##################################
path_AerosolMass_50increase = "/data/uptrop/Projects/DEFRA-NH3/GC/geosfp_eu_scale_nh3_emis/AerosolMass/2016/"

os.chdir(path_AerosolMass_50increase)
Aerosols = sorted(glob.glob("GEOSChem.AerosolMass*nc4"))

Aerosols = Aerosols[:]
Aerosols = [xr.open_dataset(file) for file in Aerosols]


GC_surface_sulfate = [data['AerMassSO4'].isel(time=0,lev=0) for data in Aerosols]
#print (GC_surface_sulfate)

#Geos-Chem Annual Mean
GC_surface_sulfate_AM = sum(GC_surface_sulfate)/len(GC_surface_sulfate)
#print (GC_surface_sulfate_AM,'AnnualMean')
print (GC_surface_sulfate_AM.shape,'AnnualMean shape')

#Geos-Chem seasonal Mean
GC_surface_sulfate_msp = sum(GC_surface_sulfate[2:9])/len(GC_surface_sulfate[2:9])
GC_surface_sulfate_mam = sum(GC_surface_sulfate[2:5])/len(GC_surface_sulfate[2:5])
#print (GC_surface_sulfate_mam.shape, 'MAM-shape')

GC_surface_sulfate_jja = sum(GC_surface_sulfate[5:8])/len(GC_surface_sulfate[5:8])
#print (GC_surface_sulfate_jja)

GC_surface_sulfate_son = sum(GC_surface_sulfate[8:11])/len(GC_surface_sulfate[8:11])
#print (GC_surface_sulfate_son)

GC_surface_sulfate_jf = sum(GC_surface_sulfate[0:2])/len(GC_surface_sulfate[0:2])
print (GC_surface_sulfate_jf, 'jf_shape')

GC_surface_sulfate_d = GC_surface_sulfate[11]
print (GC_surface_sulfate_d, 'd_shape')

#mean of JF and Dec using np.array --> creating problem in plotting
#GC_surface_sulfate_djf_a = np.array([GC_surface_sulfate_jf,GC_surface_sulfate_d])
#GC_surface_sulfate_djf = np.nanmean(GC_surface_sulfate_djf_a,axis=0)
#print (GC_surface_sulfate_djf, 'djf_shape')


GC_surface_sulfate_djf = (GC_surface_sulfate_d+GC_surface_sulfate_jf)/2
print (GC_surface_sulfate_djf, 'djf_shape')

# get GEOS-Chem lon and lat
gc_lon = GC_surface_sulfate_AM['lon']
gc_lat = GC_surface_sulfate_AM['lat']
print (len(gc_lon))
print (len(gc_lat))
print ((gc_lon))
print ((gc_lat))

# get number of sites from size of long and lat:
nsites=len(sites_lon_c)

# Define GEOS-Chem data obtained at same location as monitoring sites:
gc_data_sulphate_annual=np.zeros(nsites)
gc_data_sulphate_msp=np.zeros(nsites)
gc_data_sulphate_mam=np.zeros(nsites)
gc_data_sulphate_jja=np.zeros(nsites)
gc_data_sulphate_son=np.zeros(nsites)
gc_data_sulphate_djf=np.zeros(nsites)


#extract GEOS-Chem data using DEFRA sites lat long 
for w in range(len(sites_lat_c)):
	#print ((sites_lat[w],gc_lat))
	# lat and lon indices:
	lon_index = np.argmin(np.abs(np.subtract(sites_lon_c[w],gc_lon)))
	lat_index = np.argmin(np.abs(np.subtract(sites_lat_c[w],gc_lat)))

	#print (lon_index)
	#print (lat_index)
	gc_data_sulphate_annual[w] = GC_surface_sulfate_AM[lon_index, lat_index]
	gc_data_sulphate_msp[w] = GC_surface_sulfate_mam[lon_index, lat_index]
	gc_data_sulphate_mam[w] = GC_surface_sulfate_mam[lon_index, lat_index]
	gc_data_sulphate_jja[w] = GC_surface_sulfate_jja[lon_index, lat_index]
	gc_data_sulphate_son[w] = GC_surface_sulfate_son[lon_index, lat_index]
	gc_data_sulphate_djf[w] = GC_surface_sulfate_djf[lon_index, lat_index]

print (gc_data_sulphate_annual.shape)
print (sites_sulphate_AM.shape)

# quick scatter plot
#plt.plot(sites_sulphate_AM,gc_data_sulphate_annual,'o')
#plt.show()

# Compare DEFRA and GEOS-Chem:
#Normalized mean bias
nmb_Annual=100.*((np.nanmean(gc_data_sulphate_annual))- np.nanmean(sites_sulphate_AM_c))/np.nanmean(sites_sulphate_AM_c)
nmb_msp=100.*((np.nanmean(gc_data_sulphate_msp))- np.nanmean(sites_sulphate_msp_c))/np.nanmean(sites_sulphate_msp_c)
nmb_mam=100.*((np.nanmean(gc_data_sulphate_mam))- np.nanmean(sites_sulphate_mam_c))/np.nanmean(sites_sulphate_mam_c)
nmb_jja=100.*((np.nanmean(gc_data_sulphate_jja))- np.nanmean(sites_sulphate_jja_c))/np.nanmean(sites_sulphate_jja_c)
nmb_son=100.*((np.nanmean(gc_data_sulphate_son))- np.nanmean(sites_sulphate_son_c))/np.nanmean(sites_sulphate_son_c)
nmb_djf=100.*((np.nanmean(gc_data_sulphate_djf))- np.nanmean(sites_sulphate_djf_c))/np.nanmean(sites_sulphate_djf_c)
print(' DEFRA NMB_Annual= ', nmb_Annual)
print(' DEFRA NMB_mam = ', nmb_mam)
print(' DEFRA NMB_jja = ', nmb_jja)
print(' DEFRA NMB_son = ', nmb_son)
print(' DEFRA NMB_djf = ', nmb_djf)

#correlation
correlate_Annual=stats.pearsonr(gc_data_sulphate_annual,sites_sulphate_AM_c)

# dropping nan values and compute correlation
nas_msp = np.logical_or(np.isnan(gc_data_sulphate_msp), np.isnan(sites_sulphate_msp_c))
correlate_msp = stats.pearsonr(gc_data_sulphate_msp[~nas_msp],sites_sulphate_msp_c[~nas_msp])

nas_mam = np.logical_or(np.isnan(gc_data_sulphate_mam), np.isnan(sites_sulphate_mam_c))
correlate_mam = stats.pearsonr(gc_data_sulphate_mam[~nas_mam],sites_sulphate_mam_c[~nas_mam])

nas_jja = np.logical_or(np.isnan(gc_data_sulphate_jja), np.isnan(sites_sulphate_jja_c))
correlate_jja = stats.pearsonr(gc_data_sulphate_jja[~nas_jja],sites_sulphate_jja_c[~nas_jja])

nas_son = np.logical_or(np.isnan(gc_data_sulphate_son), np.isnan(sites_sulphate_son_c))
correlate_son = stats.pearsonr(gc_data_sulphate_son[~nas_son],sites_sulphate_son_c[~nas_son])

nas_djf = np.logical_or(np.isnan(gc_data_sulphate_djf), np.isnan(sites_sulphate_djf_c))
correlate_djf = stats.pearsonr(gc_data_sulphate_djf[~nas_djf],sites_sulphate_djf_c[~nas_djf])

print('Correlation = ',correlate_Annual)

# plotting spatial map model and DEFRA network 
os.chdir('/home/a/ap744/scratch_alok/shapefiles/GBP_shapefile')
Europe_shape = r'GBR_adm1.shp'
Europe_map = ShapelyFeature(Reader(Europe_shape).geometries(),
                               ccrs.PlateCarree(), edgecolor='black',facecolor='none')
print ('Shapefile_read')
title_list = 'DEFRA and GEOS-Chem Particulate sulfate'
title_list1 = 'Spatial Map DEFRA and GEOS-Chem Particulate sulfate'



fig2 = plt.figure(facecolor='White',figsize=[11,11]);pad= 1.1;
ax = plt.subplot(232);
#plt.title(title_list1, fontsize = 30, y=1)
ax = plt.axes(projection=ccrs.PlateCarree())
ax.add_feature(Europe_map)
ax.set_extent([-9, 3, 49, 61], crs=ccrs.PlateCarree()) # [lonW,lonE,latS,latN]

GC_surface_sulfate_msp.plot(ax=ax,cmap=cmap,vmin = 0,vmax =3,
								cbar_kwargs={'shrink': 0.0, 
											'pad' : 0.09,
											'label': '',
											'orientation':'horizontal'})

ax.scatter(x=sites_lon, y=sites_lat,c=sites_sulphate_msp,
		facecolors='none',edgecolors='black',linewidths=5,s = 100)
ax.scatter(x=sites_lon, y=sites_lat,c=sites_sulphate_msp,
		cmap=cmap,s = 100,vmin = 0,vmax = 3)
		
ax.set_title('DEFRA and GEOS-Chem Sulphate (Mar-Sep)',fontsize=15)
PCM=ax.get_children()[2] #get the mappable, the 1st and the 2nd are the x and y axes


ax.annotate('Correl_msp = {0:.2f}'.format(correlate_msp[0]),xy=(0.65,0.75), xytext=(0, pad),
		xycoords='axes fraction', textcoords='offset points',
		ha='center', va='bottom',rotation='horizontal',fontsize=20,color='w')
ax.annotate('NMB msp= {0:.2f}'.format(nmb_msp),xy=(0.65,0.85), xytext=(0, pad),
		xycoords='axes fraction', textcoords='offset points',
		ha='center', va='bottom',rotation='horizontal',fontsize=20,color='w')
		
colorbar = plt.colorbar(PCM, ax=ax,label='GEOS-Chem & DEFRA Sulphate ($\mu$g m$^{-3}$)',
                        orientation='horizontal',shrink=0.5,pad=0.01)
colorbar.ax.tick_params(labelsize=15) 
colorbar.ax.xaxis.label.set_size(15)
plt.savefig('/scratch/uptrop/ap744/python_work/'+Today_date+'sulfate_GEOS-Chem_DEFRAspatial_withoutScotland_Mar-Sep_ScaleNH3.png',bbox_inches='tight')


plt.show()
