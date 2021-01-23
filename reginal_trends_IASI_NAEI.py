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

def discrete_cmap(N, base_cmap=None):
	"""Create an N-bin discrete colormap from the specified input map"""
	# Note that if base_cmap is a string or None, you can simply do
	#    return plt.cm.get_cmap(base_cmap, N)
	# The following works for string, None, or a colormap instance:
	base = plt.cm.get_cmap(base_cmap)
	color_list = base(np.linspace(0, 1, N))
	cmap_name = base.name + str(N)
	return base.from_list(cmap_name, color_list, N)

def spatial_figure(axs,data,lons,lats,colormap,colorbar_min,colorbar_max,tb_lef=True,tb_bot=True,bad_data=False): #c_bad,c_under,c_over,c_number=20,
	"""
	input : all parameters and data rel;ated to the figure you want to plot_title
		lons and lats are 1-d array while data is 2-D array
		colorbar_min,colorbar_max specifies the minimum and maximum value you want to show with the hottest and coldest color respectively
		tb_lef and tb_bot specifies if you want to have axis labels, True fro yes
	output : a spatial map of the data
	"""
	#lons[lons>180]-=360; 
	# lon_b = np.min(lons); lon_e = np.max(lons)
	# lon_b = -180; lon_e = 180
	# lon_b = 65; lon_e = 100
	lon_b = -9; lon_e = 3 #lonW,lonE,
	
	# lat_b = np.min(lats); lat_e = np.max(lats)	
	# lat_b = -90; lat_e = 90
	# lat_b = 5; lat_e = 38
	lat_b = 49; lat_e = 61 #latS,latN
	
	lon_bin = 4; lat_bin = 4
	
	map = Basemap(lat_0=0, lon_0=0,llcrnrlon=lon_b,llcrnrlat=lat_b,urcrnrlon=lon_e,urcrnrlat=lat_e,ax=axs,projection='cyl')
	lon, lat = np.meshgrid(lons, lats)
	xi, yi = map(lon, lat)

	if tb_lef:
		map.drawparallels(np.arange(round(lat_b,0)-lat_bin, round(lat_e,0)+lat_bin, lat_bin), labels=[1,0,0,0],linewidth=0.0,fontsize=24)
	if tb_bot:
		map.drawmeridians(np.arange(round(lon_b,0), round(lon_e,0)+lon_bin, lon_bin), labels=[0,0,0,1],linewidth=0.0,fontsize=24)
	# Add Coastlines, States, and Country Boundaries
	# map.drawcoastlines(); map.drawcountries() #map.drawstates(); # draw border lines
	map.readshapefile('/scratch/uptrop/ap744/shapefiles/Shapfiles_india/World_shp/World','World',linewidth=2) # to add a shapefile on a map
	masked_obj = np.ma.masked_where(np.isnan(data), data)
	#masked_obj = maskoceans(lon,lat,masked_obj)
	cmap = discrete_cmap(20,colormap)   #  use 20 color bins, this can be changed
	cmap.set_bad([1,1,1],alpha = 1.0);
	if bad_data:
		#cmap.set_under('w');cmap.set_over('k')
		cmap.set_under('k');cmap.set_over('w')
	colormesh = map.pcolormesh(xi, yi, masked_obj,cmap=cmap,vmin=colorbar_min, vmax=colorbar_max,latlon=True)
	return colormesh	

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

iasi_derived_NH3_emission_JAN_UK = np.nansum(np.nansum(iasi_derived_NH3_emission_JAN,axis=1),axis=0)/1000
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
print (iasi_derived_NH3_emission_JAN_UK.shape, 'iasi_derived_NH3_emission_JAN_UK.shape')


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


Jan_naei_nh3_emission_UK = np.nansum(np.nansum(Jan_naei_nh3_emission,axis=1),axis=0)/1000
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
print (Jan_naei_nh3_emission_UK.shape, 'Jan_naei_nh3_emission_UK.shape')


