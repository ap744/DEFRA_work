#!/usr/bin/python
import sys
import netCDF4 as nc4
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import cartopy.feature as cfeature
from mpl_toolkits.basemap import Basemap, shiftgrid
import cartopy.crs as ccrs
import matplotlib.cm as cm
import cartopy
#cmap = cm.jet
cmap = cm.rainbow
cmap1 = cm.coolwarm
import datetime
from scipy import stats
from scipy.stats import gaussian_kde
Today_date=datetime.datetime.now().strftime("%Y%m%d")
from iris.coords import DimCoord
from iris.cube import Cube
import iris
import datetime
from netCDF4 import Dataset, num2date
from matplotlib.colors import LogNorm
import math
import scipy.io as sio
from scipy.interpolate import interp2d  as interp2d
# cmap = matplotlib.cm.get_cmap('brewer_RdBu_11')
cmap = cm.jet

Today_date=datetime.datetime.now().strftime("%Y%m%d")

def discrete_cmap(N, base_cmap=None):
	"""Create an N-bin discrete colormap from the specified input map"""
	# Note that if base_cmap is a string or None, you can simply do
	#    return plt.cm.get_cmap(base_cmap, N)
	# The following works for string, None, or a colormap instance:
	base = plt.cm.get_cmap(base_cmap)
	color_list = base(np.linspace(0, 1, N))
	cmap_name = base.name + str(N)
	return base.from_list(cmap_name, color_list, N)

def AreaWeight(lon1,lon2,lat1,lat2):
	'''
	calculate the earth radius in m2
	'''
	radius = 6371000;
	area = (math.pi/180)*np.power(radius,2)*np.abs(lon1-lon2)*(np.abs(np.sin(np.radians(lat1))-np.sin(np.radians(lat2))))
	# print np.nansum(np.nansum(area,axis=1),axis=0)
	return area

def spatial_figure(axs,data,lons,lats,colormap,colorbar_min,colorbar_max,tb_lef=True,tb_bot=True,bad_data=False): #c_bad,c_under,c_over,c_number=20,
	"""
	input : all parameters and data rel;ated to the figure you want to plot_title
		lons and lats are 1-d array while data is 2-D array
		colorbar_min,colorbar_max specifies the minimum and maximum value you want to show with the hottest and coldest color respectively
		tb_lef and tb_bot specifies if you want to have axis labels, True fro yes
	output : a spatial map of the data
	"""
	lons[lons>180]-=360; 
	# lon_b = np.min(lons); lon_e = np.max(lons)
	# lon_b = -180; lon_e = 180
	# lon_b = 65; lon_e = 100
	lon_b = -9; lon_e = 3 #lonW,lonE,
	# lat_b = np.min(lats); lat_e = np.max(lats)	
	# lat_b = -90; lat_e = 90
	# lat_b = 5; lat_e = 38
	lat_b = 49; lat_e = 61 #latS,latN
	# lon_bin = 60; lat_bin = 30
	lon_bin = 4; lat_bin = 4
	map = Basemap(lat_0=0, lon_0=0,llcrnrlon=lon_b,llcrnrlat=lat_b,urcrnrlon=lon_e,urcrnrlat=lat_e,ax=axs,projection='cyl')
	lon, lat = np.meshgrid(lons, lats)
	xi, yi = map(lon, lat)
	if tb_lef:
		map.drawparallels(np.arange(round(lat_b,0)-lat_bin, round(lat_e,0)+lat_bin, lat_bin), labels=[1,0,0,0],linewidth=0.0,fontsize=24)
	if tb_bot:
		map.drawmeridians(np.arange(round(lon_b,0), round(lon_e,0)+lon_bin, lon_bin), labels=[0,0,0,1],linewidth=0.0,fontsize=24)
	# Add Coastlines, States, and Country Boundaries
	# map.drawcoastlines(); map.drawcountries() #map.drawstates(); # draw border lines, here only coast lines
	map.readshapefile('/scratch/uptrop/ap744/shapefiles/Shapfiles_india/World_shp/World','World', linewidth=2) # to add a shapefile on a map
	masked_obj = np.ma.masked_where(np.isnan(data), data)
	#masked_obj = maskoceans(lon,lat,masked_obj)
	cmap = discrete_cmap(20,colormap)   #  use 20 color bins, this can be changed
	cmap.set_bad([1,1,1],alpha = 1.0);
	if bad_data:
		cmap.set_under('w');cmap.set_over('k')
	colormesh = map.pcolormesh(xi, yi, masked_obj,cmap=cmap,vmin=colorbar_min, vmax=colorbar_max,latlon=True)
	return colormesh

def box_clip(lon_s,lon_e,lat_s,lat_e,lon,lat,mask):
	"""
	fill the region outside the box with 0
	"""
	lon = np.array(lon)
	lat = np.array(lat)
	colum_s = [index for index in range(len(lon)) if np.abs(lon-lon_s)[index] == np.min(np.abs(lon-lon_s))][0]
	colum_e = [index for index in range(len(lon)) if np.abs(lon-lon_e)[index] == np.min(np.abs(lon-lon_e))][0]
	row_s = [index for index in range(len(lat)) if np.abs(lat-lat_s)[index] == np.min(np.abs(lat-lat_s))][0]
	row_e = [index for index in range(len(lat)) if np.abs(lat-lat_e)[index] == np.min(np.abs(lat-lat_e))][0]
	if (colum_s> colum_e):
		cache = colum_e; colum_e = colum_s; colum_s = cache;
	if (row_s> row_e):
		cache = row_e; row_e = row_s; row_s = cache;
	mask[:,0:colum_s] =0; mask[:,colum_e:-1] =0
	#plt.imshow(mask,origin='lower');plt.show()
	mask[0:row_s,:] =0; mask[row_e:-1,:] =0
	# plt.imshow(mask,origin='lower');plt.show()
	return mask	

def mask_weight(region_key,lon,lat,return_option,reverse=False):
	"""
	Read in the country mask
	interpolate it to the required resolution grids with lon_interp,lat_interp 
	crop the sepecified region eithr as a box or an administrtative polygon
	input: 
		region_ky: region name, say, India
		lon and lat of your data
	output: depent on output_option
		if output_option == 'mask': output mask (1 for mask and nan for others)
		elif output_option == 'area': output area of a mask
		elif output_option == 'area_weight': output weight of area against the total area of the mask, this is useful when you do an area-weighted mean
	"""
	lon_res = lon[1] - lon[0];lat_res = lat[1] - lat[0];
	#print (lon_res, 'lon_res')
	lons,lats = np.meshgrid(lon,lat)
	area = AreaWeight(lons,lons+lon_res,lats,lats+lat_res)
	#print (area, 'area')
	##OCEAN_MASKS FOR COUNTRIES
	ocean_mask = sio.loadmat('/scratch/uptrop/ap744/shapefiles/Euro_USA_AUS_BRICS_STA_720_360.mat')  ## change this accordingly
	lon_mask = ocean_mask['lon'][0,:];
	lat_mask = ocean_mask['lat'][0,:];
	## define your regions here
	#box_region_dic={'Wales':[-4,-3,51.5,53],'South_England':[-2.5,-1,51,52],'East_England':[0,1.5,51.5,53],'NE_England':[-2.5,-1.5,54.5,55.5],'N_Ireland':[-8,-6,54,55],'Scotland':[-5.5,-3,56.25,57.5],'All':[0,360,-90,90],'ASIA':[65,145,5,45],'US':[240,290,30,50],'ARCTIC':[0,360,60,90],'TROPICS':[0,360,-28,28],'EUROPE':[0,40,30,70],}
	box_region_dic={'SW_England':[-5.5,-2,50,54],'East_England':[1,2,50.5,54],'N_England':[-5,0,54,56],'N_Ireland':[-8,-5.5,54,55.25],'Scotland':[-4.5,1,56,58],'All':[0,360,-90,90],'ASIA':[65,145,5,45],'US':[240,290,30,50],'ARCTIC':[0,360,60,90],'TROPICS':[0,360,-28,28],'EUROPE':[0,40,30,70],}
	if (region_key == 'USA' or region_key == 'Europe' or region_key == 'India' or region_key == 'China' or region_key == 'GloLand'):
		mask= ocean_mask[region_key][:]
	elif  region_key in box_region_dic:
		mask= ocean_mask['All'][:]
		box = box_region_dic[region_key]
		mask = box_clip(box[0],box[1],box[2],box[3],lon_mask,lat_mask,mask)
	else:
		print ("error region name")
	# interpolate from 360*720 to your grids
	mask[np.isnan(mask)]=0;	mask[mask>0]=1;
	f = interp2d(lon_mask, lat_mask, mask,kind='linear'); mask = f(lon, lat);
	#plt.imshow(mask,origin='lower');plt.show()
	mask[mask >= 1] = 1;mask[mask < 1] = 0;
	# weight each grid cell by its area weight against the total area
	if reverse:    ## note this Flase by default, but can be used to exclude the specified region from a larger map
		mask=1-mask
	mask[mask==0] = np.nan
	grid_area=np.multiply(mask,area); 
	mask_weighted = np.divide(grid_area,np.nansum(np.nansum(grid_area,axis=1),axis=0))
	if return_option == 'mask': return mask
	elif return_option == 'area': return grid_area
	elif return_option == 'area_weight': return mask_weighted
	
def days_months(months):
	""" Calculate number of days in a month """
	if months in [1,3,5,7,8,10,12]:
		days=np.arange(1,32)
	elif months in [4,6,9,11]:
		days=np.arange(1,31)
	else:
		days=np.arange(1,30) #as feb 2016 has 29 days
	return days

def daily_data(month,day):
	NA=6.022e23   #molecules/mol
	mNH3=17.0      #g(NO2)/mol
	mair=28.97    #g(air)/mol
	#satellite data files
	def create_filename_sat(month,day):
		"""
		# define file names to be read in each loop
		"""
		if month<=9:
			month = '0'+str(month);
		else:
			month =str(month);
		#print (month, 'iN @ Month')
		if day<=9:
			day = '0'+str(day);
		else:
			day =str(day);
		#print (day, 'iN @ Day')
		sat_data_files = '/scratch/uptrop/em440/for_Alok/gc_ncdf/satellite_files/ts_08_11.EU.2016'+str(month)+str(day)+'.nc'
		
		return sat_data_files
	
	def create_filename_emission(month,day):
		"""
		# define file names to be read in each loop
		"""
		if month<=9:
			month = '0'+str(month);
		else:
			month =str(month);
		print (month, 'iN @ Month')
		if day<=9:
			day = '0'+str(day);
		else:
			day =str(day);
		#print (day, 'iN @ Day')
		emissions_data_files = '/scratch/uptrop/em440/for_Alok/gc_ncdf/emissions/HEMCO_diagnostics.2016'+str(month)+str(day)+'0000.nc'
		return emissions_data_files
	#Satellites daily files 
	sat_data_files = create_filename_sat(month,day)
	ncf_sat = nc4.Dataset(sat_data_files,mode='r')
	lat_sat = ncf_sat.variables['LAT'][:]
	lon_sat = ncf_sat.variables['LON'][:]
	nh3_GC_column = ncf_sat.variables['IJ-AVG-S__NH3'][:]     		#NH3 tracer 'ppbv'
	airdensity_sat = ncf_sat.variables['TIME-SER__AIRDEN'][:]	#Air density 'molecules/cm3'
	bxheight_sat = ncf_sat.variables['BXHGHT-S__BXHEIGHT'][:]	#Grid Box height 'm'
	#print (nh3_GC_column.shape, airdensity_sat.shape, bxheight_sat.shape)
	bxheight1_sat = bxheight_sat*100 #Grid Box height 'cm'
	airdensity1_sat = airdensity_sat * bxheight1_sat # Air density 'molecules/cm3' * Grid Box height 'cm' = molecules/cm2
	nh3_GC_column_A = (nh3_GC_column/1e9)*airdensity1_sat#molucules/cm2
	#print (nh3_GC_column_A.shape)
	nh3_GC_column_B = np.nansum(nh3_GC_column_A, axis=0) #sum over all model vertical layers #molucules/cm2
	#print (nh3_GC_column_B.shape)
	#nh3_GC_column_C = nh3_GC_column_B/NA  #unit moles (NH3) /cm2
	#print (nh3_GC_column_C.shape)
	#emissions daily files
	emission_data_files = create_filename_emission(month,day)
	ncf_emission = nc4.Dataset(emission_data_files,mode='r')
	lat_emission = ncf_emission.variables['lat'][:]
	lon_emission = ncf_emission.variables['lon'][:]
	#area_emission = ncf_emission.variables['AREA'][:]  				#unit m2
	nh3_emission_total = ncf_emission.variables['EmisNH3_Total'][:]  	#Unit kg
	#nh3_emission_anthro = ncf_emission.variables['EmisNH3_Anthro'][:] 	#Unit kg
	#print (area_emission.shape, 'area_emission.shape')
	#print (nh3_emission_total.shape, 'nh3_emission_total.shape')
	nh3_emission_total_A = nh3_emission_total[0,:,:,:]
	#print (nh3_emission_total_A.shape, 'nh3_emission_total_A.shape')
	#sum over all vertical layers
	nh3_emission_total_B = np.nansum(nh3_emission_total_A, axis=0)			#kg  --> sum over all vertical layers
	#print (nh3_emission_total_B.shape, 'nh3_emission_total_B.shape')
	##below 6 lines to convert kg to molecules/cm2
	#nh3_emission_total_C = nh3_emission_total_B/(area_emission*1.0e4) 		#kg(NH3)/cm2
	#print (nh3_emission_total_C.shape, 'nh3_emission_total_C.shape')
	#nh3_emission_total_D = nh3_emission_total_C/(mNH3*1.0e-3)           	#moles(NH3)/cm2
	#print (nh3_emission_total_D.shape, 'nh3_emission_total_D.shape')
	#nh3_emission_total_E = nh3_emission_total_D*NA                      	#molecules/cm2
	#print (nh3_emission_total_E.shape, 'nh3_emission_total_E.shape')
	#print (lat_GC_column.shape, lon_GC_column.shape, 'lat lon shape of sat file')
	#print (lat_emission.shape, lon_emission.shape, 'lat lon shape of emission file')
	return lat_sat,lon_sat,nh3_GC_column_B, lat_emission,lon_emission,nh3_emission_total_B

def monthly_mean_cal():	
	months=np.arange(1,13)
	time_series = np.empty(len(months))

	GC_column_mon_mean = np.empty((len(time_series),115,177))
	GC_column_mon_mean[:] = np.nan
	
	emission_mon_sum = np.empty((len(time_series),115,177))
	emission_mon_sum[:] = np.nan
	
	for imonth in months:
		GC_column_nh3_mon_mean = np.empty((115,177))
		GC_column_nh3_mon_mean[:] = np.nan
		
		emission_nh3_mon_mean = np.empty((115,177))
		emission_nh3_mon_mean[:] = np.nan
				
		days = days_months(imonth)
		for iday in days:	
			lat_sat,lon_sat,nh3_GC_column_B, lat_emission,lon_emission,nh3_emission_total_B = daily_data(imonth,iday)
			GC_column_nh3_mon_mean = np.dstack((GC_column_nh3_mon_mean,nh3_GC_column_B))
			emission_nh3_mon_mean = np.dstack((emission_nh3_mon_mean,nh3_emission_total_B))
			
			#print (GC_column_nh3_mon_mean.shape)
		GC_column_mon_mean[imonth-1,:,:] = np.nanmean(GC_column_nh3_mon_mean,axis=2)
		#emission_mon_mean[imonth-1,:,:] = np.nanmean(emission_nh3_mon_mean,axis=2)
		emission_mon_sum[imonth-1,:,:] = np.nansum(emission_nh3_mon_mean,axis=2)
	#print (lat_sat.shape, lon_sat.shape, 'lat lon shape of sat file')
	#print (lat_emission.shape, lon_emission.shape, 'lat lon shape of emission file')	
	
	return time_series, lat_sat, lon_sat, emission_mon_sum, GC_column_mon_mean 

time_series, lat, lon, emission_mon_sum, GC_column_mon_mean = monthly_mean_cal()
#print(GC_column_mon_mean.shape,'!GC_column_mon_mean.shape')
#print(emission_mon_sum.shape,'!emission_mon_sum.shape')

#area from emission 0.25x0.3125
area_file = nc4.Dataset('/scratch/uptrop/em440/for_Alok/gc_ncdf/emissions/HEMCO_diagnostics.201608180000.nc',mode='r')
area_raw = area_file.variables['AREA'][:]
#print (area_raw.shape, 'area_raw.shape')

data_emission1=np.empty((12, 115, 177))
data_emission1[:]=np.nan

for imon in range(12):
	data_emission1[imon,:,:] = emission_mon_sum[imon,:,:]/area_raw
#print (data_emission1.shape, 'data_emission1.shape')

#regridding using iris
lat_min,lon_min = np.nanmin(lat),np.nanmin(lon)
lat_max,lon_max = np.nanmax(lat),np.nanmax(lon)
lat01 = np.arange(lat_min, lat_max, 0.1)
lon01 = np.arange(lon_min, lon_max, 0.1)

latitude = DimCoord(lat,
					standard_name='latitude',
					units='degrees')
longitude = DimCoord(lon,
					standard_name='longitude',
					units='degrees')
time = DimCoord(np.linspace(1, 12, 12),
					standard_name='time',
					units='month')
#print (time)

cube1 = Cube(GC_column_mon_mean,
					dim_coords_and_dims=[(latitude, 1),
										(longitude, 2),
										(time, 0)])

cube2 = Cube(data_emission1,
					dim_coords_and_dims=[(latitude, 1),
										(longitude, 2),
										(time, 0)])

regridded_data_GC_column = cube1.interpolate([('latitude', lat01), ('longitude', lon01)],
                           iris.analysis.Linear())
#print(regridded_data_GC_column.shape,'regrid_GC_column_shape')

regridded_data_emission = cube2.interpolate([('latitude', lat01), ('longitude', lon01)],
                           iris.analysis.Linear())
#print(regridded_data_emission, 'regrid_emission_shape')

lat_n = regridded_data_emission.coord('latitude')
lat_n =lat_n.points[:]
lon_n = regridded_data_emission.coord('longitude')
lon_n =lon_n.points[:]

lat_n_min,lon_n_min = np.nanmin(lat_n),np.nanmin(lon_n)
lat_n_max,lon_n_max = np.nanmax(lat_n),np.nanmax(lon_n)

lat_gc_uk = lat_n[172:279]
#print (lat_gc_uk.shape, lat_gc_uk, 'lat_gc_uk_shape')
lon_gc_uk = lon_n[50:176]
#print (lon_gc_uk.shape, lon_gc_uk, 'lon_gc_uk_shape')
regridded_data_emission = regridded_data_emission[:].data
regridded_data_emission_uk_GC = regridded_data_emission[:,172:279,50:176].copy()
#print (regridded_data_emission_uk_GC.shape , 'regridded_data_emission_uk_GC.shape')
regridded_data_GC_column = regridded_data_GC_column[:].data
regridded_data_GC_column_uk = regridded_data_GC_column[:,172:279,50:176]
#print (regridded_data_GC_column_uk.shape, 'regridded_data_GC_column_uk.shape')

#area from emission 0.1x0.1
area_fileB = nc4.Dataset('/scratch/uptrop/em440/for_Alok/naei_nh3/NAEI_total_NH3_0.1x0.1_2016.nc',mode='r')
area_regid = area_fileB.variables['area'][:]
#print (area_regid.shape, 'area_regid.shape')
area_regid_uk = area_regid[7:114,4:130]
#print (area_regid_uk.shape, 'area_regid_uk.shape')

data_emission2=np.empty((12, 107, 126))
data_emission2[:]=np.nan

for imo in range(12):
	data_emission2[imo,:,:] = regridded_data_emission_uk_GC[imo,:,:]*area_regid_uk
	#print (data_emission1.shape, 'data_emission1.shape')
#print (data_GC_column2.shape, 'data_GC_column1.shape')

###############################################################
###############################################################
##########      IASI derived NH$_3$ Emission           ########
###############################################################
###############################################################

#Reading IASI column concentration
iasi_nh3_file = nc4.Dataset('/scratch/uptrop/em440/for_Alok/iasi_ncdf/iasi_nh3_uk_oversampled_2008-2018_0.1_jul2020.nc',mode='r')
lat_iasi = iasi_nh3_file.variables['lat'][:]
lon_iasi = iasi_nh3_file.variables['lon'][:]
iasi_nh3 = iasi_nh3_file.variables['iasi_nh3'][:] #unit molecules/cm2
lat_iasi_min,lon_iasi_min = np.nanmin(lat_iasi),np.nanmin(lon_iasi)
lat_iasi_max,lon_iasi_max = np.nanmax(lat_iasi),np.nanmax(lon_iasi)
#print (lat_iasi_min, 'lat_min_iasi')
#print (lon_iasi_min, 'lon_min_iasi')
#print (lat_iasi_max, 'lat_max_iasi')
#print (lon_iasi_max, 'lon_max_iasi')
lat_iasi_uk = lat_iasi[1:108]
#print (lat_iasi_uk.shape, lat_iasi_uk, 'lat_iasi_uk_shape')
lon_iasi_uk = lon_iasi[1:127]
#print (lon_iasi_uk.shape, lon_iasi_uk, 'lon_iasi_uk_shape')
#print (iasi_nh3.shape, 'iasi_nh3.shape')
iasi_nh3_uk = iasi_nh3[:,1:108,1:127]
#print (iasi_nh3_uk.shape, 'iasi_nh3_uk.shape')
iasi_nh3_uk[iasi_nh3_uk <= 0] = np.nan

ratio_GC_emission_Column_jan = data_emission2[0,:,:]/regridded_data_GC_column_uk[0,:,:]
ratio_GC_emission_Column_feb = data_emission2[1,:,:]/regridded_data_GC_column_uk[1,:,:]
ratio_GC_emission_Column_mar = data_emission2[2,:,:]/regridded_data_GC_column_uk[2,:,:]
ratio_GC_emission_Column_apr = data_emission2[3,:,:]/regridded_data_GC_column_uk[3,:,:]
ratio_GC_emission_Column_may = data_emission2[4,:,:]/regridded_data_GC_column_uk[4,:,:]
ratio_GC_emission_Column_jun = data_emission2[5,:,:]/regridded_data_GC_column_uk[5,:,:]
ratio_GC_emission_Column_jul = data_emission2[6,:,:]/regridded_data_GC_column_uk[6,:,:]
ratio_GC_emission_Column_aug = data_emission2[7,:,:]/regridded_data_GC_column_uk[7,:,:]
ratio_GC_emission_Column_sep = data_emission2[8,:,:]/regridded_data_GC_column_uk[8,:,:]
ratio_GC_emission_Column_oct = data_emission2[9,:,:]/regridded_data_GC_column_uk[9,:,:]
ratio_GC_emission_Column_nov = data_emission2[10,:,:]/regridded_data_GC_column_uk[10,:,:]
ratio_GC_emission_Column_dec = data_emission2[11,:,:]/regridded_data_GC_column_uk[11,:,:]

JAN_IASI_column = iasi_nh3_uk[0,:,:]  #10$^{15}$molecules/cm$^2$
FEB_IASI_column = iasi_nh3_uk[1,:,:] 
MAR_IASI_column = iasi_nh3_uk[2,:,:] 
APR_IASI_column = iasi_nh3_uk[3,:,:] 
MAY_IASI_column = iasi_nh3_uk[4,:,:]  #10$^{15}$molecules/cm$^2$
JUN_IASI_column = iasi_nh3_uk[5,:,:] 
JUL_IASI_column = iasi_nh3_uk[6,:,:] 
AUG_IASI_column = iasi_nh3_uk[7,:,:] 
SEP_IASI_column = iasi_nh3_uk[8,:,:]  #10$^{15}$molecules/cm$^2$
OCT_IASI_column = iasi_nh3_uk[9,:,:] 
NOV_IASI_column = iasi_nh3_uk[10,:,:] 
DEC_IASI_column = iasi_nh3_uk[11,:,:] 

iasi_derived_NH3_emission_JAN = (ratio_GC_emission_Column_jan * JAN_IASI_column)/1000
iasi_derived_NH3_emission_FEB = (ratio_GC_emission_Column_feb * FEB_IASI_column)/1000
iasi_derived_NH3_emission_MAR = (ratio_GC_emission_Column_mar * MAR_IASI_column)/1000
iasi_derived_NH3_emission_APR = (ratio_GC_emission_Column_apr * APR_IASI_column)/1000
iasi_derived_NH3_emission_MAY = (ratio_GC_emission_Column_may * MAY_IASI_column)/1000
iasi_derived_NH3_emission_JUN = (ratio_GC_emission_Column_jun * JUN_IASI_column)/1000
iasi_derived_NH3_emission_JUL = (ratio_GC_emission_Column_jul * JUL_IASI_column)/1000
iasi_derived_NH3_emission_AUG = (ratio_GC_emission_Column_aug * AUG_IASI_column)/1000
iasi_derived_NH3_emission_SEP = (ratio_GC_emission_Column_sep * SEP_IASI_column)/1000
iasi_derived_NH3_emission_OCT = (ratio_GC_emission_Column_oct * OCT_IASI_column)/1000
iasi_derived_NH3_emission_NOV = (ratio_GC_emission_Column_nov * NOV_IASI_column)/1000
iasi_derived_NH3_emission_DEC = (ratio_GC_emission_Column_dec * DEC_IASI_column)/1000


#################################################################################################
################################################ NAEI EMISSION ##################################
#################################################################################################

#calculating annual emission
annual_emission = np.nansum(data_emission2.data[:], axis=0)

#monthly scale factor
Jan_scale_factor = data_emission2[0,:,:]/annual_emission #unit - unitless(kg/kg from GC model)
Feb_scale_factor = data_emission2[1,:,:]/annual_emission
Mar_scale_factor = data_emission2[2,:,:]/annual_emission
Apr_scale_factor = data_emission2[3,:,:]/annual_emission
May_scale_factor = data_emission2[4,:,:]/annual_emission
Jun_scale_factor = data_emission2[5,:,:]/annual_emission
Jul_scale_factor = data_emission2[6,:,:]/annual_emission
Aug_scale_factor = data_emission2[7,:,:]/annual_emission
Sep_scale_factor = data_emission2[8,:,:]/annual_emission
Oct_scale_factor = data_emission2[9,:,:]/annual_emission
Nov_scale_factor = data_emission2[10,:,:]/annual_emission
Dec_scale_factor = data_emission2[11,:,:]/annual_emission
#print (Jan_scale_factor.shape, 'Jan_scale_factor.shape')


#Reading NAEI emission data
naei_nh3_file = nc4.Dataset('/scratch/uptrop/em440/for_Alok/naei_nh3/NAEI_total_NH3_0.1x0.1_2016.nc',mode='r')
lat_naei = naei_nh3_file.variables['lat'][:]
lon_naei = naei_nh3_file.variables['lon'][:]
naei_nh3 = naei_nh3_file.variables['NH3'][:] 	#unit g/m2/yr
naei_area = naei_nh3_file.variables['area'][:] 	#unit m2

naei_nh3_area = (naei_nh3 * naei_area )/1000 # g/m2/yr * m2 = g/yr --> g/yr/1000 --->kg/yr
#naei_nh3_area_mon = naei_nh3_area/12 # kg/month
naei_nh3_area_mon = naei_nh3_area.copy()

naei_nh3_area_mon[naei_nh3_area_mon<100] = np.nan
#naei_nh3_area_mon = np.where(naei_nh3_area_mon<100, np.nan, naei_nh3_area_mon)

lat_naei_min,lon_naei_min = np.nanmin(lat_naei),np.nanmin(lon_naei)
lat_naei_max,lon_naei_max = np.nanmax(lat_naei),np.nanmax(lon_naei)
#print (lat_naei_min, 'lat_min_naei')
#print (lon_naei_min, 'lon_min_naei')
#print (lat_naei_max, 'lat_max_naei')
#print (lon_naei_max, 'lon_max_naei')

lat_naei_uk = lat_naei[7:114]
#print (lat_naei_uk.shape, lat_naei_uk, 'lat_naei_uk_shape')
lon_naei_uk = lon_naei[4:130]
#print (lon_naei_uk.shape, lon_naei_uk, 'lon_naei_uk_shape')

#print (naei_nh3_area_mon.shape, 'naei_nh3_area_mon.shape')
naei_nh3_uk = naei_nh3_area_mon[7:114,4:130]
#print (naei_nh3_uk.shape, 'naei_nh3_uk.shape')

UK_mask = naei_nh3_uk.copy()
UK_mask[UK_mask<100] = np.nan
UK_mask[UK_mask>100] = 1


#mask using np.where
#UK_mask = np.where(UK_mask > 100, 1, np.nan)

############################ NAEI MONTHLY EMISSION ######################################
Jan_naei_nh3_emission = (Jan_scale_factor *  naei_nh3_uk)/1000
Feb_naei_nh3_emission = (Feb_scale_factor *  naei_nh3_uk)/1000
Mar_naei_nh3_emission = (Mar_scale_factor *  naei_nh3_uk)/1000
Apr_naei_nh3_emission = (Apr_scale_factor *  naei_nh3_uk)/1000
May_naei_nh3_emission = (May_scale_factor *  naei_nh3_uk)/1000
Jun_naei_nh3_emission = (Jun_scale_factor *  naei_nh3_uk)/1000
Jul_naei_nh3_emission = (Jul_scale_factor *  naei_nh3_uk)/1000
Aug_naei_nh3_emission = (Aug_scale_factor *  naei_nh3_uk)/1000
Sep_naei_nh3_emission = (Sep_scale_factor *  naei_nh3_uk)/1000
Oct_naei_nh3_emission = (Oct_scale_factor *  naei_nh3_uk)/1000
Nov_naei_nh3_emission = (Nov_scale_factor *  naei_nh3_uk)/1000
Dec_naei_nh3_emission = (Dec_scale_factor *  naei_nh3_uk)/1000
#print (Jan_naei_nh3_emission.shape, 'Jan_naei_nh3_emission.shape')


##################################################################################
############################ IASI after UK Mask ##################################
##################################################################################
iasi_derived_NH3_emission_JAN = iasi_derived_NH3_emission_JAN.copy() * UK_mask
iasi_derived_NH3_emission_FEB = iasi_derived_NH3_emission_FEB.copy() * UK_mask
iasi_derived_NH3_emission_MAR = iasi_derived_NH3_emission_MAR.copy() * UK_mask
iasi_derived_NH3_emission_APR = iasi_derived_NH3_emission_APR.copy() * UK_mask
iasi_derived_NH3_emission_MAY = iasi_derived_NH3_emission_MAY.copy() * UK_mask
iasi_derived_NH3_emission_JUN = iasi_derived_NH3_emission_JUN.copy() * UK_mask
iasi_derived_NH3_emission_JUL = iasi_derived_NH3_emission_JUL.copy() * UK_mask
iasi_derived_NH3_emission_AUG = iasi_derived_NH3_emission_AUG.copy() * UK_mask
iasi_derived_NH3_emission_SEP = iasi_derived_NH3_emission_SEP.copy() * UK_mask
iasi_derived_NH3_emission_OCT = iasi_derived_NH3_emission_OCT.copy() * UK_mask
iasi_derived_NH3_emission_NOV = iasi_derived_NH3_emission_NOV.copy() * UK_mask
iasi_derived_NH3_emission_DEC = iasi_derived_NH3_emission_DEC.copy() * UK_mask
print (iasi_derived_NH3_emission_JAN.shape, 'iasi_derived_NH3_emission_JAN.shape')

iasi_derived_NH3_emission_year = np.stack((iasi_derived_NH3_emission_JAN,iasi_derived_NH3_emission_FEB,iasi_derived_NH3_emission_MAR,iasi_derived_NH3_emission_APR,iasi_derived_NH3_emission_MAY,iasi_derived_NH3_emission_JUN,iasi_derived_NH3_emission_JUL,iasi_derived_NH3_emission_AUG,iasi_derived_NH3_emission_SEP,iasi_derived_NH3_emission_OCT,iasi_derived_NH3_emission_NOV,iasi_derived_NH3_emission_DEC),axis=0)
print (iasi_derived_NH3_emission_year.shape,'iasi_derived_NH3_emission_year')
iasi_derived_NH3_emission_JAN_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_JAN,axis=1),axis=0)/1000
#print (iasi_derived_NH3_emission_JAN_UK, 'iasi_derived_NH3_emission_JAN_UK')
iasi_derived_NH3_emission_FEB_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_FEB,axis=1),axis=0)/1000
iasi_derived_NH3_emission_MAR_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_MAR,axis=1),axis=0)/1000
iasi_derived_NH3_emission_APR_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_APR,axis=1),axis=0)/1000
iasi_derived_NH3_emission_MAY_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_MAY,axis=1),axis=0)/1000
iasi_derived_NH3_emission_JUN_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_JUN,axis=1),axis=0)/1000
iasi_derived_NH3_emission_JUL_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_JUL,axis=1),axis=0)/1000
iasi_derived_NH3_emission_AUG_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_AUG,axis=1),axis=0)/1000
iasi_derived_NH3_emission_SEP_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_SEP,axis=1),axis=0)/1000
iasi_derived_NH3_emission_OCT_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_OCT,axis=1),axis=0)/1000
iasi_derived_NH3_emission_NOV_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_NOV,axis=1),axis=0)/1000
iasi_derived_NH3_emission_DEC_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_DEC,axis=1),axis=0)/1000



####################################################################################
############################ NAEI after IASI Mask ##################################
####################################################################################

#new_arr=np.where(((old_array1!=np.nan)&(old_array2!=np.nan)),np.multiply(old_array1,old_array2),np.nan)
#iasi_derived_NH3_emission_JAN[iasi_derived_NH3_emission_JAN>0] =1
#iasi_derived_NH3_emission_JAN[iasi_derived_NH3_emission_JAN<0] = np.nan


iasi_mask_jan = iasi_derived_NH3_emission_JAN.copy()
iasi_mask_jan[iasi_mask_jan>0] =1
iasi_mask_jan[iasi_mask_jan<0] =np.nan

iasi_mask_feb = iasi_derived_NH3_emission_FEB.copy()
iasi_mask_feb[iasi_mask_feb>0] =1
iasi_mask_feb[iasi_mask_feb<0] =np.nan

iasi_mask_mar = iasi_derived_NH3_emission_MAR.copy()
iasi_mask_mar[iasi_mask_mar>0] =1
iasi_mask_mar[iasi_mask_mar<0] =np.nan

iasi_mask_apr = iasi_derived_NH3_emission_APR.copy()
iasi_mask_apr[iasi_mask_apr>0] =1
iasi_mask_apr[iasi_mask_apr<0] =np.nan


iasi_mask_may = iasi_derived_NH3_emission_MAY.copy()
iasi_mask_may[iasi_mask_may>0] =1
iasi_mask_may[iasi_mask_may<0] =np.nan

iasi_mask_jun = iasi_derived_NH3_emission_JUN.copy()
iasi_mask_jun[iasi_mask_jun>0] =1
iasi_mask_jun[iasi_mask_jun<0] =np.nan

iasi_mask_jul = iasi_derived_NH3_emission_JUL.copy()
iasi_mask_jul[iasi_mask_jul>0] =1
iasi_mask_jul[iasi_mask_jul<0] =np.nan

iasi_mask_aug = iasi_derived_NH3_emission_AUG.copy()
iasi_mask_aug[iasi_mask_aug>0] =1
iasi_mask_aug[iasi_mask_aug<0] =np.nan


iasi_mask_sep = iasi_derived_NH3_emission_SEP.copy()
iasi_mask_sep[iasi_mask_sep>0] =1
iasi_mask_sep[iasi_mask_sep<0] =np.nan

iasi_mask_oct = iasi_derived_NH3_emission_OCT.copy()
iasi_mask_oct[iasi_mask_oct>0] =1
iasi_mask_oct[iasi_mask_oct<0] =np.nan

iasi_mask_nov = iasi_derived_NH3_emission_NOV.copy()
iasi_mask_nov[iasi_mask_nov>0] =1
iasi_mask_nov[iasi_mask_nov<0] =np.nan

iasi_mask_dec = iasi_derived_NH3_emission_DEC.copy()
iasi_mask_dec[iasi_mask_dec>0] =1
iasi_mask_dec[iasi_mask_dec<0] =np.nan

#iasi_mask_jan = np.where(iasi_derived_NH3_emission_JAN > 1, 1, np.nan)
#iasi_mask_feb = np.where(iasi_derived_NH3_emission_FEB > 1, 1, np.nan)
#iasi_mask_mar = np.where(iasi_derived_NH3_emission_MAR > 1, 1, np.nan)
#iasi_mask_apr = np.where(iasi_derived_NH3_emission_APR > 1, 1, np.nan)
#iasi_mask_may = np.where(iasi_derived_NH3_emission_MAY > 1, 1, np.nan)
#iasi_mask_jun = np.where(iasi_derived_NH3_emission_JUN > 1, 1, np.nan)
#iasi_mask_jul = np.where(iasi_derived_NH3_emission_JUL > 1, 1, np.nan)
#iasi_mask_aug = np.where(iasi_derived_NH3_emission_AUG > 1, 1, np.nan)
#iasi_mask_sep = np.where(iasi_derived_NH3_emission_SEP > 1, 1, np.nan)
#iasi_mask_oct = np.where(iasi_derived_NH3_emission_OCT > 1, 1, np.nan)
#iasi_mask_nov = np.where(iasi_derived_NH3_emission_NOV > 1, 1, np.nan)
#iasi_mask_dec = np.where(iasi_derived_NH3_emission_DEC > 1, 1, np.nan)

#Jan_naei_nh3_emission = np.where(((Jan_naei_nh3_emission!=np.nan) & (iasi_mask_jan!=np.nan)),np.multiply(Jan_naei_nh3_emission,iasi_mask_jan),np.nan)

Jan_naei_nh3_emission = Jan_naei_nh3_emission*iasi_mask_jan
Feb_naei_nh3_emission = Feb_naei_nh3_emission*iasi_mask_feb
Mar_naei_nh3_emission = Mar_naei_nh3_emission*iasi_mask_mar
Apr_naei_nh3_emission = Apr_naei_nh3_emission*iasi_mask_apr
May_naei_nh3_emission = May_naei_nh3_emission*iasi_mask_may
Jun_naei_nh3_emission = Jun_naei_nh3_emission*iasi_mask_jun
Jul_naei_nh3_emission = Jul_naei_nh3_emission*iasi_mask_jul
Aug_naei_nh3_emission = Aug_naei_nh3_emission*iasi_mask_aug
Sep_naei_nh3_emission = Sep_naei_nh3_emission*iasi_mask_sep
Oct_naei_nh3_emission = Oct_naei_nh3_emission*iasi_mask_oct
Nov_naei_nh3_emission = Nov_naei_nh3_emission*iasi_mask_nov
Dec_naei_nh3_emission = Dec_naei_nh3_emission*iasi_mask_dec
print (Jan_naei_nh3_emission.shape, 'Jan_naei_nh3_emission.shape')

year_naei_nh3_emission = np.stack((Jan_naei_nh3_emission,Feb_naei_nh3_emission,Mar_naei_nh3_emission,Apr_naei_nh3_emission,May_naei_nh3_emission,Jun_naei_nh3_emission,Jul_naei_nh3_emission,Aug_naei_nh3_emission,Sep_naei_nh3_emission,Oct_naei_nh3_emission,Nov_naei_nh3_emission,Dec_naei_nh3_emission),axis =0)
print (year_naei_nh3_emission.shape, 'year_naei_nh3_emission')


Jan_naei_nh3_emission_UK = np.nansum(np.nansum(Jan_naei_nh3_emission,axis=1),axis=0)/1000
#print (Jan_naei_nh3_emission_UK, 'Jan_naei_nh3_emission_UK')
Feb_naei_nh3_emission_UK = np.nansum(np.nansum(Feb_naei_nh3_emission,axis=1),axis=0)/1000
Mar_naei_nh3_emission_UK = np.nansum(np.nansum(Mar_naei_nh3_emission,axis=1),axis=0)/1000
Apr_naei_nh3_emission_UK = np.nansum(np.nansum(Apr_naei_nh3_emission,axis=1),axis=0)/1000
May_naei_nh3_emission_UK = np.nansum(np.nansum(May_naei_nh3_emission,axis=1),axis=0)/1000
Jun_naei_nh3_emission_UK = np.nansum(np.nansum(Jun_naei_nh3_emission,axis=1),axis=0)/1000
Jul_naei_nh3_emission_UK = np.nansum(np.nansum(Jul_naei_nh3_emission,axis=1),axis=0)/1000
Aug_naei_nh3_emission_UK = np.nansum(np.nansum(Aug_naei_nh3_emission,axis=1),axis=0)/1000
Sep_naei_nh3_emission_UK = np.nansum(np.nansum(Sep_naei_nh3_emission,axis=1),axis=0)/1000
Oct_naei_nh3_emission_UK = np.nansum(np.nansum(Oct_naei_nh3_emission,axis=1),axis=0)/1000
Nov_naei_nh3_emission_UK = np.nansum(np.nansum(Nov_naei_nh3_emission,axis=1),axis=0)/1000
Dec_naei_nh3_emission_UK = np.nansum(np.nansum(Dec_naei_nh3_emission,axis=1),axis=0)/1000

################################## Extracting Regional Data  ####################################
lat = lat_naei_uk
lon = lon_naei_uk
#print (lat, 'lat')
#print (lon, 'lon')

print (iasi_derived_NH3_emission_year.shape, 'iasi_derived_NH3_emission_year')
SW_England_IASI		= np.nansum(np.nansum(iasi_derived_NH3_emission_year[:,1:41,55:85],axis=2),axis=1)
print (SW_England_IASI.shape, 'SW_England_IASI.shape')
SW_England_NAEI		= np.nansum(np.nansum(year_naei_nh3_emission[:,1:41,55:85],axis=2),axis=1)

East_England_IASI	= np.nansum(np.nansum(iasi_derived_NH3_emission_year[:,5:41,85:122],axis=2),axis=1)
East_England_NAEI	= np.nansum(np.nansum(year_naei_nh3_emission[:,5:41,85:122],axis=2),axis=1)

N_England_IASI		= np.nansum(np.nansum(iasi_derived_NH3_emission_year[:,41:61,55:105],axis=2),axis=1)
N_England_NAEI		= np.nansum(np.nansum(year_naei_nh3_emission[:,41:61,55:105],axis=2),axis=1)

N_Ireland_IASI		= np.nansum(np.nansum(iasi_derived_NH3_emission_year[:,41:53,21:55],axis=2),axis=1)
N_Ireland_NAEI		= np.nansum(np.nansum(year_naei_nh3_emission[:,41:53,21:55],axis=2),axis=1)


SW_England_IASI_mar_sep = SW_England_IASI[2:9]/1000
SW_England_NAEI_mar_sep = SW_England_NAEI[2:9]/1000
East_England_IASI_mar_sep = East_England_IASI[2:9]/1000
East_England_NAEI_mar_sep = East_England_NAEI[2:9]/1000
N_England_IASI_mar_sep = N_England_IASI[2:9]/1000
N_England_NAEI_mar_sep = N_England_NAEI[2:9]/1000
N_Ireland_IASI_mar_sep = N_Ireland_IASI[2:9]/1000
N_Ireland_NAEI_mar_sep = N_Ireland_NAEI[2:9]/1000

tot_IASI_SW = round(np.sum(SW_England_IASI_mar_sep),2)
tot_NAEI_SW = round(np.sum(SW_England_NAEI_mar_sep),2)

tot_IASI_E_Eng = round(np.sum(East_England_IASI_mar_sep),2)
tot_NAEI_E_Eng = round(np.sum(East_England_NAEI_mar_sep),2)

tot_IASI_N_Eng = round(np.sum(N_England_IASI_mar_sep),2)
tot_NAEI_N_Eng = round(np.sum(N_England_NAEI_mar_sep),2)

tot_IASI_N_Ireland = round(np.sum(N_Ireland_IASI_mar_sep),2)
tot_NAEI_N_Ireland = round(np.sum(N_Ireland_NAEI_mar_sep),2)



####################################################################################################
#####################    IASI uncertainty quadrature   #############################################
####################################################################################################
def IASI_uncertainty():
	###############################################################
	###############################################################
	##########    		  	IASI  NH$_3$          		   ########
	###############################################################
	###############################################################

	#Reading IASI column concentration
	iasi_nh3_file = nc4.Dataset('/scratch/uptrop/em440/for_Alok/iasi_ncdf/iasi_nh3_uk_oversampled_2008-2018_0.1_sep2020.nc',mode='r')
	lat_iasi = iasi_nh3_file.variables['lat'][:]
	lon_iasi = iasi_nh3_file.variables['lon'][:]
	iasi_nh3 = iasi_nh3_file.variables['iasi_nh3'][:] #unit molecules/cm2
	iasi_uncertainty = iasi_nh3_file.variables['iasi_uncertainty'][:] #unit molecules/cm2

	lat_iasi_min,lon_iasi_min = np.nanmin(lat_iasi),np.nanmin(lon_iasi)
	lat_iasi_max,lon_iasi_max = np.nanmax(lat_iasi),np.nanmax(lon_iasi)
	#print (lat_iasi_min, 'lat_min_iasi')
	#print (lon_iasi_min, 'lon_min_iasi')
	#print (lat_iasi_max, 'lat_max_iasi')
	#print (lon_iasi_max, 'lon_max_iasi')

	lat_iasi_uk = lat_iasi[1:108]
	#print (lat_iasi_uk.shape, lat_iasi_uk, 'lat_iasi_uk_shape')
	lon_iasi_uk = lon_iasi[1:127]
	#print (lon_iasi_uk.shape, lon_iasi_uk, 'lon_iasi_uk_shape')

	#print (iasi_nh3.shape, 'iasi_nh3.shape')
	iasi_nh3_uk = iasi_nh3[:,1:108,1:127]
	#print (iasi_nh3_uk.shape, 'iasi_nh3_uk.shape')
	iasi_nh3_uk[iasi_nh3_uk <= 0] = np.nan


	#print (iasi_uncertainty.shape, 'iasi_uncertainty.shape')
	iasi_uncertainty_uk = iasi_uncertainty[:,1:108,1:127]
	#print (iasi_uncertainty_uk.shape, 'iasi_uncertainty_uk.shape')
	#iasi_uncertainty_uk[iasi_uncertainty_uk <= 0] = np.nan



	#Reading NAEI emission data
	naei_nh3_file = nc4.Dataset('/scratch/uptrop/em440/for_Alok/naei_nh3/NAEI_total_NH3_0.1x0.1_2016.nc',mode='r')
	lat_naei = naei_nh3_file.variables['lat'][:]
	lon_naei = naei_nh3_file.variables['lon'][:]
	naei_nh3 = naei_nh3_file.variables['NH3'][:] 	#unit g/m2/yr
	naei_area = naei_nh3_file.variables['area'][:] 	#unit m2

	naei_nh3_area = (naei_nh3 * naei_area )/1000 # g/m2/yr * m2 = g/yr --> g/yr/1000 --->kg/yr
	#naei_nh3_area_mon = naei_nh3_area/12 # kg/month
	naei_nh3_area_mon = naei_nh3_area.copy()

	naei_nh3_area_mon[naei_nh3_area_mon<100] = np.nan
	#naei_nh3_area_mon = np.where(naei_nh3_area_mon<100, np.nan, naei_nh3_area_mon)

	lat_naei_min,lon_naei_min = np.nanmin(lat_naei),np.nanmin(lon_naei)
	lat_naei_max,lon_naei_max = np.nanmax(lat_naei),np.nanmax(lon_naei)
	#print (lat_naei_min, 'lat_min_naei')
	#print (lon_naei_min, 'lon_min_naei')
	#print (lat_naei_max, 'lat_max_naei')
	#print (lon_naei_max, 'lon_max_naei')

	lat_naei_uk = lat_naei[7:114]
	#print (lat_naei_uk.shape, lat_naei_uk, 'lat_naei_uk_shape')
	lon_naei_uk = lon_naei[4:130]
	#print (lon_naei_uk.shape, lon_naei_uk, 'lon_naei_uk_shape')

	#print (naei_nh3_area_mon.shape, 'naei_nh3_area_mon.shape')
	naei_nh3_uk = naei_nh3_area_mon[7:114,4:130]
	#print (naei_nh3_uk.shape, 'naei_nh3_uk.shape')

	UK_mask = naei_nh3_uk.copy()
	UK_mask[UK_mask<100] = np.nan
	UK_mask[UK_mask>100] = 1



	for imo in range(12):
		iasi_nh3_uk[imo,:,:] = iasi_nh3_uk[imo,:,:]*UK_mask
		iasi_uncertainty_uk[imo,:,:] = iasi_uncertainty_uk[imo,:,:]*UK_mask
		

	##################    IASI Column NH3    ##############################
	JAN_IASI_column = iasi_nh3_uk[0,:,:] /1e15#10$^{15}$molecules/cm$^2$
	FEB_IASI_column = iasi_nh3_uk[1,:,:] /1e15
	MAR_IASI_column = iasi_nh3_uk[2,:,:] /1e15
	APR_IASI_column = iasi_nh3_uk[3,:,:] /1e15
	MAY_IASI_column = iasi_nh3_uk[4,:,:] /1e15 #10$^{15}$molecules/cm$^2$
	JUN_IASI_column = iasi_nh3_uk[5,:,:] /1e15
	JUL_IASI_column = iasi_nh3_uk[6,:,:] /1e15
	AUG_IASI_column = iasi_nh3_uk[7,:,:] /1e15
	SEP_IASI_column = iasi_nh3_uk[8,:,:] /1e15 #10$^{15}$molecules/cm$^2$
	OCT_IASI_column = iasi_nh3_uk[9,:,:] /1e15
	NOV_IASI_column = iasi_nh3_uk[10,:,:] /1e15
	DEC_IASI_column = iasi_nh3_uk[11,:,:] /1e15
	#print (np.nanmax(JUL_IASI_column), np.nanmin(JUL_IASI_column), 'max min JUL_IASI_column')

	##################    IASI Column UNCERTAINTY  ##############################
	JAN_IASI_uncertainty = iasi_uncertainty_uk[0,:,:] /1e15 #10$^{15}$molecules/cm$^2$
	FEB_IASI_uncertainty = iasi_uncertainty_uk[1,:,:] /1e15
	MAR_IASI_uncertainty = iasi_uncertainty_uk[2,:,:] /1e15
	APR_IASI_uncertainty = iasi_uncertainty_uk[3,:,:] /1e15
	MAY_IASI_uncertainty = iasi_uncertainty_uk[4,:,:] /1e15 #10$^{15}$molecules/cm$^2$
	JUN_IASI_uncertainty = iasi_uncertainty_uk[5,:,:] /1e15
	JUL_IASI_uncertainty = iasi_uncertainty_uk[6,:,:] /1e15
	AUG_IASI_uncertainty = iasi_uncertainty_uk[7,:,:] /1e15
	SEP_IASI_uncertainty = iasi_uncertainty_uk[8,:,:] /1e15 #10$^{15}$molecules/cm$^2$
	OCT_IASI_uncertainty = iasi_uncertainty_uk[9,:,:] /1e15
	NOV_IASI_uncertainty = iasi_uncertainty_uk[10,:,:] /1e15
	DEC_IASI_uncertainty = iasi_uncertainty_uk[11,:,:] /1e15

	#print (np.nanmax(JUL_IASI_uncertainty), np.nanmin(JUL_IASI_uncertainty), 'max min JUL_IASI_uncertainty')

	##################    IASI Column UNCERTAINTY  Percentage ##############################
	JAN_IASI_uncertaintyP = (iasi_uncertainty_uk[0,:,:]/iasi_nh3_uk[0,:,:])*100
	FEB_IASI_uncertaintyP = (iasi_uncertainty_uk[1,:,:]/iasi_nh3_uk[1,:,:])*100
	MAR_IASI_uncertaintyP = (iasi_uncertainty_uk[2,:,:]/iasi_nh3_uk[2,:,:])*100 
	APR_IASI_uncertaintyP = (iasi_uncertainty_uk[3,:,:]/iasi_nh3_uk[3,:,:])*100 
	MAY_IASI_uncertaintyP = (iasi_uncertainty_uk[4,:,:]/iasi_nh3_uk[4,:,:])*100
	JUN_IASI_uncertaintyP = (iasi_uncertainty_uk[5,:,:]/iasi_nh3_uk[5,:,:])*100 
	JUL_IASI_uncertaintyP = (iasi_uncertainty_uk[6,:,:]/iasi_nh3_uk[6,:,:])*100
	AUG_IASI_uncertaintyP = (iasi_uncertainty_uk[7,:,:]/iasi_nh3_uk[7,:,:])*100
	SEP_IASI_uncertaintyP = (iasi_uncertainty_uk[8,:,:]/iasi_nh3_uk[8,:,:])*100
	OCT_IASI_uncertaintyP = (iasi_uncertainty_uk[9,:,:]/iasi_nh3_uk[9,:,:])*100
	NOV_IASI_uncertaintyP = (iasi_uncertainty_uk[10,:,:]/iasi_nh3_uk[10,:,:])*100
	DEC_IASI_uncertaintyP = (iasi_uncertainty_uk[11,:,:]/iasi_nh3_uk[11,:,:])*100
	
	mar_uncertainty_mask = MAR_IASI_uncertaintyP.copy()
	mar_uncertainty_mask[mar_uncertainty_mask <=0] = np.nan
	mar_uncertainty_mask[mar_uncertainty_mask <=50] = 1
	mar_uncertainty_mask[mar_uncertainty_mask >50] = np.nan
	MAR_IASI_column = MAR_IASI_column*mar_uncertainty_mask
	
	apr_uncertainty_mask = APR_IASI_uncertaintyP.copy()
	apr_uncertainty_mask[apr_uncertainty_mask <=0] = np.nan
	apr_uncertainty_mask[apr_uncertainty_mask <=50] = 1
	apr_uncertainty_mask[apr_uncertainty_mask >50] = np.nan
	APR_IASI_column = APR_IASI_column*apr_uncertainty_mask

	may_uncertainty_mask = MAY_IASI_uncertaintyP.copy()
	may_uncertainty_mask[may_uncertainty_mask <=0] = np.nan
	may_uncertainty_mask[may_uncertainty_mask <=50] = 1
	may_uncertainty_mask[may_uncertainty_mask >50] = np.nan
	MAY_IASI_column = MAY_IASI_column*may_uncertainty_mask
	
	jun_uncertainty_mask = JUN_IASI_uncertaintyP.copy()
	jun_uncertainty_mask[jun_uncertainty_mask <=0] = np.nan
	jun_uncertainty_mask[jun_uncertainty_mask <=50] = 1
	jun_uncertainty_mask[jun_uncertainty_mask >50] = np.nan
	JUN_IASI_column = JUN_IASI_column*jun_uncertainty_mask
	
	jul_uncertainty_mask = JUL_IASI_uncertaintyP.copy()
	jul_uncertainty_mask[jul_uncertainty_mask <=0] = np.nan
	jul_uncertainty_mask[jul_uncertainty_mask <=50] = 1
	jul_uncertainty_mask[jul_uncertainty_mask >50] = np.nan
	JUL_IASI_column = JUL_IASI_column*jul_uncertainty_mask
	
	aug_uncertainty_mask = AUG_IASI_uncertaintyP.copy()
	aug_uncertainty_mask[aug_uncertainty_mask <=0] = np.nan
	aug_uncertainty_mask[aug_uncertainty_mask <=50] = 1
	aug_uncertainty_mask[aug_uncertainty_mask >50] = np.nan
	AUG_IASI_column = AUG_IASI_column*aug_uncertainty_mask
		
	
	sep_uncertainty_mask = SEP_IASI_uncertaintyP.copy()
	sep_uncertainty_mask[sep_uncertainty_mask <=0] = np.nan
	sep_uncertainty_mask[sep_uncertainty_mask <=50] = 1
	sep_uncertainty_mask[sep_uncertainty_mask >50] = np.nan
	SEP_IASI_column = SEP_IASI_column*sep_uncertainty_mask


### Spatial Quadrature ####
	mar_uncertainty_cal = MAR_IASI_uncertaintyP.copy()*1e-2*mar_uncertainty_mask
	mar_uncertainty_cal[mar_uncertainty_cal >.50] = np.nan
	print (mar_uncertainty_cal.shape, 'mar_uncertainty_cal.shape')
	mar_spatial_quadrature = np.sqrt(np.nansum(np.square(mar_uncertainty_cal)))
	print (mar_spatial_quadrature, 'mar_spatial_quadrature')
	
	apr_uncertainty_cal = APR_IASI_uncertaintyP.copy()*1e-2*apr_uncertainty_mask
	apr_uncertainty_cal[apr_uncertainty_cal >.50] = np.nan
	apr_spatial_quadrature = np.sqrt(np.nansum(np.square(apr_uncertainty_cal)))
	print (apr_spatial_quadrature, 'apr_spatial_quadrature')
	may_uncertainty_cal = MAY_IASI_uncertaintyP.copy()*1e-2*may_uncertainty_mask
	may_uncertainty_cal[may_uncertainty_cal >.50] = np.nan
	may_spatial_quadrature = np.sqrt(np.nansum(np.square(may_uncertainty_cal)))
	print (may_spatial_quadrature, 'may_spatial_quadrature')
	jun_uncertainty_cal = JUN_IASI_uncertaintyP.copy()*1e-2*jun_uncertainty_mask
	jun_uncertainty_cal[jun_uncertainty_cal >.50] = np.nan
	jun_spatial_quadrature = np.sqrt(np.nansum(np.square(jun_uncertainty_cal)))
	print (jun_spatial_quadrature, 'jun_spatial_quadrature')
	jul_uncertainty_cal = JUL_IASI_uncertaintyP.copy()*1e-2*jul_uncertainty_mask
	jul_uncertainty_cal[jul_uncertainty_cal >.50] = np.nan
	jul_spatial_quadrature = np.sqrt(np.nansum(np.square(jul_uncertainty_cal)))
	print (jul_spatial_quadrature, 'jul_spatial_quadrature')
	aug_uncertainty_cal = AUG_IASI_uncertaintyP.copy()*1e-2*aug_uncertainty_mask
	aug_uncertainty_cal[aug_uncertainty_cal >.50] = np.nan
	aug_spatial_quadrature = np.sqrt(np.nansum(np.square(aug_uncertainty_cal)))
	print (aug_spatial_quadrature, 'aug_spatial_quadrature')
	sep_uncertainty_cal = SEP_IASI_uncertaintyP.copy()*1e-2*sep_uncertainty_mask
	sep_uncertainty_cal[sep_uncertainty_cal >.50] = np.nan
	sep_spatial_quadrature = np.sqrt(np.nansum(np.square(sep_uncertainty_cal)))	
	print (sep_spatial_quadrature, 'sep_spatial_quadrature')	
	
	"""### Spatial Quadrature ####
	mar_uncertainty_cal = MAR_IASI_uncertaintyP.copy()/100
	mar_uncertainty_cal[mar_uncertainty_cal >.50] = np.nan
	print (mar_uncertainty_cal.shape, 'mar_uncertainty_cal.shape')
	mar_spatial_quadrature = np.sqrt(np.nansum(np.square(mar_uncertainty_cal)))
	print (mar_spatial_quadrature, 'mar_spatial_quadrature')
	
	apr_uncertainty_cal = APR_IASI_uncertaintyP.copy()/100
	apr_uncertainty_cal[apr_uncertainty_cal >.50] = np.nan
	apr_spatial_quadrature = np.sqrt(np.nansum(np.square(apr_uncertainty_cal)))
	print (apr_spatial_quadrature, 'apr_spatial_quadrature')
	may_uncertainty_cal = MAY_IASI_uncertaintyP.copy()/100
	may_uncertainty_cal[may_uncertainty_cal >.50] = np.nan
	may_spatial_quadrature = np.sqrt(np.nansum(np.square(may_uncertainty_cal)))
	print (may_spatial_quadrature, 'may_spatial_quadrature')
	jun_uncertainty_cal = JUN_IASI_uncertaintyP.copy()/100
	jun_uncertainty_cal[jun_uncertainty_cal >.50] = np.nan
	jun_spatial_quadrature = np.sqrt(np.nansum(np.square(jun_uncertainty_cal)))
	print (jun_spatial_quadrature, 'jun_spatial_quadrature')
	jul_uncertainty_cal = JUL_IASI_uncertaintyP.copy()/100
	jul_uncertainty_cal[jul_uncertainty_cal >.50] = np.nan
	jul_spatial_quadrature = np.sqrt(np.nansum(np.square(jul_uncertainty_cal)))
	print (jul_spatial_quadrature, 'jul_spatial_quadrature')
	aug_uncertainty_cal = AUG_IASI_uncertaintyP.copy()/100
	aug_uncertainty_cal[aug_uncertainty_cal >.50] = np.nan
	aug_spatial_quadrature = np.sqrt(np.nansum(np.square(aug_uncertainty_cal)))
	print (aug_spatial_quadrature, 'aug_spatial_quadrature')
	sep_uncertainty_cal = SEP_IASI_uncertaintyP.copy()/100
	sep_uncertainty_cal[sep_uncertainty_cal >.50] = np.nan
	sep_spatial_quadrature = np.sqrt(np.nansum(np.square(sep_uncertainty_cal)))	
	print (sep_spatial_quadrature, 'sep_spatial_quadrature')"""
	
	
	Mar_Sep_iasi = np.stack([MAR_IASI_column, APR_IASI_column, MAY_IASI_column, JUN_IASI_column, JUL_IASI_column, AUG_IASI_column, SEP_IASI_column])
	mar_sep_iasi_mean_after_uncertainty50 = np.nanmean(Mar_Sep_iasi, axis=0)
	
	mar_sep_quadrature = np.sqrt((np.square(MAR_IASI_uncertainty))+(np.square(APR_IASI_uncertainty))+(np.square(MAY_IASI_uncertainty))+(np.square(JUN_IASI_uncertainty))+(np.square(JUL_IASI_uncertainty))+(np.square(AUG_IASI_uncertainty))+(np.square(SEP_IASI_uncertainty)))
	
	mar_sep_uncertaintyP = (mar_sep_quadrature/mar_sep_iasi_mean_after_uncertainty50)*100
	
	
	mar_sep_uncertainty_cal = mar_sep_uncertaintyP.copy()/100
	mar_sep_uncertainty_cal[mar_sep_uncertainty_cal >.50] = np.nan
	mar_sep_uncertainty_cal_spatial_quadrature = np.sqrt(np.nansum(np.square(mar_sep_uncertainty_cal)))
	#print (mar_sep_uncertainty_cal_spatial_quadrature, 'mar_sep_uncertainty_cal_spatial_quadrature')
	
	### quadrature of Spatial Quadrature ####
	
	mar_sep_spatial_quadrature = np.sqrt((np.square(mar_spatial_quadrature))+(np.square(apr_spatial_quadrature))+(np.square(may_spatial_quadrature))+(np.square(jun_spatial_quadrature))+(np.square(jul_spatial_quadrature))+(np.square(aug_spatial_quadrature))+(np.square(sep_spatial_quadrature)))
	#print (mar_sep_spatial_quadrature, '!mar_sep_spatial_quadrature!')
	
	
	
	return mar_uncertainty_cal, apr_uncertainty_cal, may_uncertainty_cal, jun_uncertainty_cal, jul_uncertainty_cal, aug_uncertainty_cal, sep_uncertainty_cal

	
mar_uncertainty_cal, apr_uncertainty_cal, may_uncertainty_cal, jun_uncertainty_cal, jul_uncertainty_cal, aug_uncertainty_cal, sep_uncertainty_cal = IASI_uncertainty()


SW_England_IASI_mar_error	= np.sqrt(np.nansum(np.square(mar_uncertainty_cal[1:41,55:85])))
SW_England_IASI_apr_error	= np.sqrt(np.nansum(np.square(apr_uncertainty_cal[1:41,55:85])))
SW_England_IASI_may_error	= np.sqrt(np.nansum(np.square(may_uncertainty_cal[1:41,55:85])))
SW_England_IASI_jun_error	= np.sqrt(np.nansum(np.square(jun_uncertainty_cal[1:41,55:85])))
SW_England_IASI_jul_error	= np.sqrt(np.nansum(np.square(jul_uncertainty_cal[1:41,55:85])))
SW_England_IASI_aug_error	= np.sqrt(np.nansum(np.square(aug_uncertainty_cal[1:41,55:85])))
SW_England_IASI_sep_error	= np.sqrt(np.nansum(np.square(sep_uncertainty_cal[1:41,55:85])))

East_England_IASI_mar_error	= np.sqrt(np.nansum(np.square(mar_uncertainty_cal[5:41,85:122])))
East_England_IASI_apr_error	= np.sqrt(np.nansum(np.square(apr_uncertainty_cal[5:41,85:122])))
East_England_IASI_may_error	= np.sqrt(np.nansum(np.square(may_uncertainty_cal[5:41,85:122])))
East_England_IASI_jun_error	= np.sqrt(np.nansum(np.square(jun_uncertainty_cal[5:41,85:122])))
East_England_IASI_jul_error	= np.sqrt(np.nansum(np.square(jul_uncertainty_cal[5:41,85:122])))
East_England_IASI_aug_error	= np.sqrt(np.nansum(np.square(aug_uncertainty_cal[5:41,85:122])))
East_England_IASI_sep_error	= np.sqrt(np.nansum(np.square(sep_uncertainty_cal[5:41,85:122])))

N_England_IASI_mar_error	= np.sqrt(np.nansum(np.square(mar_uncertainty_cal[41:61,55:105])))
N_England_IASI_apr_error	= np.sqrt(np.nansum(np.square(apr_uncertainty_cal[41:61,55:105])))
N_England_IASI_may_error	= np.sqrt(np.nansum(np.square(may_uncertainty_cal[41:61,55:105])))
N_England_IASI_jun_error	= np.sqrt(np.nansum(np.square(jun_uncertainty_cal[41:61,55:105])))
N_England_IASI_jul_error	= np.sqrt(np.nansum(np.square(jul_uncertainty_cal[41:61,55:105])))
N_England_IASI_aug_error	= np.sqrt(np.nansum(np.square(aug_uncertainty_cal[41:61,55:105])))
N_England_IASI_sep_error	= np.sqrt(np.nansum(np.square(sep_uncertainty_cal[41:61,55:105])))

N_Ireland_England_IASI_mar_error	= np.sqrt(np.nansum(np.square(mar_uncertainty_cal[41:53,21:55])))
N_Ireland_England_IASI_apr_error	= np.sqrt(np.nansum(np.square(apr_uncertainty_cal[41:53,21:55])))
N_Ireland_England_IASI_may_error	= np.sqrt(np.nansum(np.square(may_uncertainty_cal[41:53,21:55])))
N_Ireland_England_IASI_jun_error	= np.sqrt(np.nansum(np.square(jun_uncertainty_cal[41:53,21:55])))
N_Ireland_England_IASI_jul_error	= np.sqrt(np.nansum(np.square(jul_uncertainty_cal[41:53,21:55])))
N_Ireland_England_IASI_aug_error	= np.sqrt(np.nansum(np.square(aug_uncertainty_cal[41:53,21:55])))
N_Ireland_England_IASI_sep_error	= np.sqrt(np.nansum(np.square(sep_uncertainty_cal[41:53,21:55])))








print (SW_England_IASI_mar_error, 'SW_England_IASI_mar_error')
SW_England_IASI_mar_sep_error = [SW_England_IASI_mar_error, SW_England_IASI_apr_error, SW_England_IASI_may_error,SW_England_IASI_jun_error, SW_England_IASI_jul_error, SW_England_IASI_aug_error,SW_England_IASI_sep_error]
print (SW_England_IASI_mar_sep_error, 'SW_England_IASI_mar_sep_error')
East_England_IASI_mar_sep_error = [East_England_IASI_mar_error, East_England_IASI_apr_error, East_England_IASI_may_error,East_England_IASI_jun_error, East_England_IASI_jul_error, East_England_IASI_aug_error,East_England_IASI_sep_error]
N_England_IASI_mar_sep_error = [N_England_IASI_mar_error, N_England_IASI_apr_error, N_England_IASI_may_error,N_England_IASI_jun_error, N_England_IASI_jul_error, N_England_IASI_aug_error,N_England_IASI_sep_error]
N_Ireland_England_IASI_mar_sep_error = [N_Ireland_England_IASI_mar_error, N_Ireland_England_IASI_apr_error, N_Ireland_England_IASI_may_error,N_Ireland_England_IASI_jun_error, N_Ireland_England_IASI_jul_error, N_Ireland_England_IASI_aug_error,N_Ireland_England_IASI_sep_error]



SW_England_NAEI_mar_sep_error = (SW_England_NAEI_mar_sep *31)/100
East_England_NAEI_mar_sep_error = (East_England_NAEI_mar_sep*31)/100
N_England_NAEI_mar_sep_error = (N_England_NAEI_mar_sep*31)/100
N_Ireland_NAEI_mar_sep_error = (N_Ireland_NAEI_mar_sep*31)/100


X = np.linspace(1,7,7)
Y = np.linspace(1.11,7.11,7)
#print (X)


fig = plt.figure(facecolor='White',figsize=[32,21]);pad= 0.5; 
# plt.suptitle ('Vertical Profile NO$_2$ ', fontsize = 32, y=0.95)

ax = fig.add_subplot(221)
plt.errorbar(X, SW_England_IASI_mar_sep, yerr =SW_England_IASI_mar_sep_error, capsize=11, c='m',linewidth=5)
plt.errorbar(Y, SW_England_NAEI_mar_sep, yerr = SW_England_NAEI_mar_sep_error, capsize=11, c='c',linestyle='-',linewidth=5)
plt.title('SW England',fontsize = 35, y=1.01)
plt.ylabel('NH$_3$ Emission (Gg)', fontsize = 35, y =0.5)
plt.text(6.4, 19.5, str(tot_IASI_SW), fontsize=12, c='m')
plt.text(6.4, 17.5, str(tot_NAEI_SW), fontsize=12, c='c')
#plt.xlabel('Months', fontsize = 25, y=0.01)
tick_locs = [1,3,5,7]
tick_lbls = ['Mar','May','Jul','Sep']
plt.xticks(tick_locs, tick_lbls, fontsize = 35)
plt.ylim(0, 25)
plt.yticks(fontsize = 35)
ax.yaxis.get_offset_text().set_size(35)
plt.legend(('IASI' ,'NAEI'),fontsize=32,loc='upper center')

ax = fig.add_subplot(222)
plt.errorbar(X, East_England_IASI_mar_sep, yerr = East_England_IASI_mar_sep_error, capsize=11, c='m',linewidth=5)
plt.errorbar(Y, East_England_NAEI_mar_sep, yerr = East_England_NAEI_mar_sep_error, capsize=11, c='c',linestyle='-',linewidth=5)
plt.title('East England',fontsize = 35, y=1.01)
plt.ylabel('NH$_3$ Emission (Gg)', fontsize = 35, y =0.5)
plt.text(6.4, 19.5, str(tot_IASI_E_Eng), fontsize=12, c='m')
plt.text(6.4, 17.5, str(tot_NAEI_E_Eng), fontsize=12, c='c')
#plt.xlabel('Months', fontsize = 25, y=0.01)
tick_locs = [1,3,5,7]
tick_lbls = ['Mar','May','Jul','Sep']
plt.xticks(tick_locs, tick_lbls, fontsize = 35)
plt.ylim(0, 25)
plt.yticks(fontsize = 35)
ax.yaxis.get_offset_text().set_size(35)
plt.legend(('IASI' ,'NAEI'),fontsize=32,loc='upper center')

ax = fig.add_subplot(223)
plt.errorbar(X, N_England_IASI_mar_sep, yerr = N_England_IASI_mar_sep_error, capsize=11, c='m',linewidth=5)
plt.errorbar(Y, N_England_NAEI_mar_sep, yerr = N_England_NAEI_mar_sep_error, capsize=11, c='c',linestyle='-',linewidth=5)
plt.title('North England',fontsize = 35, y=1.01)
plt.ylabel('NH$_3$ Emission (Gg)', fontsize = 35, y =0.5)
plt.text(6.4, 19.5, str(tot_IASI_N_Eng), fontsize=12, c='m')
plt.text(6.4, 17.5, str(tot_NAEI_N_Eng), fontsize=12, c='c')
#plt.xlabel('Months', fontsize = 25, y=0.01)
tick_locs = [1,3,5,7]
tick_lbls = ['Mar','May','Jul','Sep']
plt.xticks(tick_locs, tick_lbls, fontsize = 35)
plt.ylim(0, 25)
plt.yticks(fontsize = 35)
ax.yaxis.get_offset_text().set_size(35)
plt.legend(('IASI' ,'NAEI'),fontsize=32,loc='upper center')

ax = fig.add_subplot(224)
plt.errorbar(X, N_Ireland_IASI_mar_sep, yerr = N_Ireland_England_IASI_mar_sep_error, capsize=11, c='m',linewidth=5)
plt.errorbar(Y, N_Ireland_NAEI_mar_sep, yerr = N_Ireland_NAEI_mar_sep_error, capsize=11, c='c',linestyle='-',linewidth=5)
plt.title('North Ireland',fontsize = 35, y=1.01)
plt.ylabel('NH$_3$ Emission (Gg)', fontsize = 35, y =0.5)
plt.text(6.4, 19.5, str(tot_IASI_N_Ireland), fontsize=12, c='m')
plt.text(6.4, 17.5, str(tot_NAEI_N_Ireland), fontsize=12, c='c')
#plt.xlabel('Months', fontsize = 25, y=0.01)
tick_locs = [1,3,5,7]
tick_lbls = ['Mar','May','Jul','Sep']
plt.xticks(tick_locs, tick_lbls, fontsize = 35)
plt.ylim(0, 25)
plt.yticks(fontsize = 35)
ax.yaxis.get_offset_text().set_size(35)
plt.legend(('IASI' ,'NAEI'),fontsize=32,loc='upper center')

plt.subplots_adjust(left=0.05, bottom=0.07, right=0.98, top=0.97, wspace=0.25, hspace=0.20);
plt.savefig('/scratch/uptrop/ap744/python_work/'+Today_date+'_A7a_regional_trends_IASI_NAEI_e_error_test.png',bbox_inches='tight')   ##########	
#fig.savefig('/scratch/uptrop/ap744/python_work/'+Today_date+'_A7a_regional_trends_IASI_NAEI_e_error.ps', format='ps')
plt.show()
