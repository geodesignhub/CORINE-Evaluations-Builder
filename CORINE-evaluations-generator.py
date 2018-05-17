import json, geojson, requests
import random, os, sys, shutil
import GeodesignHub, ShapelyHelper, config
from shapely.geometry.base import BaseGeometry
from shapely.geometry import shape, mapping, shape, asShape
from shapely.geometry import MultiPolygon, MultiPoint, MultiLineString
from shapely.ops import unary_union
from urllib.parse import urlparse
from os.path import splitext, basename
import zipfile	
import re	
import fiona
from fiona.crs import from_epsg
from shapely.geometry import box
from shapely.ops import unary_union

class DataDownloader():
	def downloadFiles(self, urls):
		for url in urls: 
			disassembled = urlparse(url)
			filename = basename(disassembled.path)
			ext = os.path.splitext(disassembled.path)[1]
			cwd = os.getcwd()
			outputdirectory = os.path.join(cwd,config.settings['workingdirectory'])
			if not os.path.exists(outputdirectory):
				os.mkdir(outputdirectory)
			local_filename = os.path.join(outputdirectory, filename)
			if not os.path.exists(local_filename):
				print("Downloading from %s..." % url)
				r = requests.get(url, stream=True)
				with open(local_filename, 'wb') as f:
				    for chunk in r.iter_content(chunk_size=1024): 
				        if chunk: # filter out keep-alive new chunks
				            f.write(chunk)
				            #f.flush() commented by recommendation from J.F.Sebastian
			if ext == '.zip':
				shapefilelist = self.unzipFile(local_filename)

		return shapefilelist

	def readFile(self, filename):
		cwd = os.getcwd()
		workingdirectory = os.path.join(cwd,config.settings['workingdirectory'])

		if not os.path.exists(workingdirectory):
			os.mkdir(workingdirectory)
		print(workingdirectory, filename)
		filepath = os.path.join(workingdirectory, filename)	
		ext = os.path.splitext(filepath)[1]
		shapefilelist = []
		try:
			assert os.path.exists(filepath)
		except AssertionError as ae:
			print("Input file does not exist %s" % ae)
		else:
			if ext == '.zip':
				shapefilelist = self.unzipFile(filepath)

		return shapefilelist

			
			
	def unzipFile(self, zippath):
		# zip_ref = zipfile.ZipFile(zippath, 'r')
		print("Unzipping archive.. %s" % zippath)
		cwd = os.getcwd()
		workingdirectory = os.path.join(cwd,config.settings['workingdirectory'])
		shapefilelist = []
		fh = open(zippath, 'rb')
		z = zipfile.ZipFile(fh)
		for name in z.namelist():
			basename= os.path.basename(name)
			filename, file_extension = os.path.splitext(basename)
			if file_extension == '.shp' and 'MACOSX' not in name:

				shapefilelist.append(name)
			z.extract(name, workingdirectory)
		fh.close()

		return shapefilelist


class AOIClipper():
	''' A class clip source data to AOI'''
	def clipFile(self, aoibbox, corinefile):
		# print aoibbox, osmfile, clipkey
		# schema of the new shapefile
		
		# creation of the new shapefile with the intersection

		opshp = corinefile
		cwd = os.getcwd()
		clippeddirectory = os.path.join(cwd,config.settings['workingdirectory'], 'clipped')
		if not os.path.exists(clippeddirectory):
			os.mkdir(clippeddirectory)

		outputdirectory = os.path.join(cwd,config.settings['workingdirectory'])
		opfile = os.path.join(clippeddirectory, opshp)

		corinefile = os.path.join(outputdirectory, corinefile)
	
		with fiona.open(corinefile) as source:
			schema = source.schema
			with fiona.open(opfile, 'w',crs=from_epsg(4326), driver='ESRI Shapefile', schema=schema) as sink:
				# Process only the records intersecting a box.
				for f in source.filter(bbox=aoibbox):  
					prop = f['properties']
					
					sink.write({'geometry':mapping(shape(f['geometry'])),'properties': prop})
		return corinefile


class EvaluationBuilder():
	def __init__(self, systemname):

		self.redFeatures = []
		self.yellowFeatures = []
		self.greenFeatures = []
		self.systemname = systemname
		self.symdifference = 0
		self.colorDict = {'red':self.redFeatures, 'yellow':self.yellowFeatures, 'green':self.greenFeatures}

	def processFile(self, color, corinefile,corinecodes):
		curfeatures = self.colorDict[color]
		cwd = os.getcwd()

		with fiona.open(corinefile) as source:
			for feature in source: 
				try: 
					# print(corinecodes, type(feature['properties']['code_12']))
					if int(feature['properties']['code_12']) in corinecodes:
						
						curfeatures.append(feature)		
				except KeyError as ke:
					pass
		self.colorDict[color] = curfeatures


	def createSymDifference(self):
		prjbbox = config.settings['aoibounds']
		bbox= box(prjbbox[0],prjbbox[1], prjbbox[2], prjbbox[3])
		allExistingFeatures = []

		for color, colorfeatures in self.colorDict.items():
			for curcolorfeature in colorfeatures:
				if curcolorfeature['geometry']['type'] == 'GeometryCollection':
					pass
				else:
					try:
						s = asShape(curcolorfeature['geometry'])
					except Exception as e: 
						pass
					else:
						if s.is_valid:
							allExistingFeatures.append(s)
		allExistingFeaturesUnion = unary_union(allExistingFeatures)

		difference = bbox.difference(allExistingFeaturesUnion)
		self.symdifference = difference

	def dissolveColors(self):
		colorDict = self.colorDict
		try:
			cd = {}
			for color, colorFeatures in colorDict.items():
				allExistingcolorfeatures = []
				for curcolorfeature in colorFeatures:
					try:
						s = asShape(curcolorfeature['geometry'])
					except Exception as e: 
						pass
					else:
						if s.is_valid:
							allExistingcolorfeatures.append(s)
				allExistingcolorfeaturesUnion = unary_union(allExistingcolorfeatures)
				if allExistingcolorfeaturesUnion.geom_type == 'MultiPolygon':
					tmpfs = []
					allExistingColorUnion = [polygon for polygon in allExistingcolorfeaturesUnion]
					for existingUnionPolygon in allExistingColorUnion:
						g = json.loads(ShapelyHelper.export_to_JSON(existingUnionPolygon))
						tmpf = {'type':'Feature','properties':{'areatype':color}, 'geometry':g }
						tmpfs.append(tmpf)
					cd[color] = tmpfs

				else:
					g = json.loads(ShapelyHelper.export_to_JSON(allExistingcolorfeaturesUnion))
					tmpf = {'type':'Feature','properties':{'areatype':color}, 'geometry':g }
					cd[color] = [tmpf]
		except Exception as e: 
			# if the unary union fails fail gracefully 
			pass
		else:
			self.colorDict = cd

	def writeEvaluationFile(self):
		opgeojson = self.systemname + '.geojson'
		cwd = os.getcwd()
		outputdirectory = os.path.join(cwd,config.settings['outputdirectory'])
		if not os.path.exists(outputdirectory):
			os.mkdir(outputdirectory)
		opfile = os.path.join(outputdirectory, opgeojson)
		fc = {"type":"FeatureCollection", "features":[]}
		for color, colorfeatures in self.colorDict.items():
			for curcolorfeature in colorfeatures:
				# print curcolorfeature
				f = json.loads(ShapelyHelper.export_to_JSON(curcolorfeature))
				f['properties']={}
				f['properties']['areatype'] = color.lower()
				fc['features'].append(f)

		if self.symdifference:
			geom_type= self.symdifference.geom_type
			if geom_type =='MultiPolygon':
				for geom in self.symdifference.geoms:
					symdiffindfeat = ShapelyHelper.export_to_JSON(geom)
					tmpf = {'type':'Feature','properties':{'areatype':'yellow'}, 'geometry':json.loads(symdiffindfeat)}
					fc['features'].append((tmpf))
			elif geom_type == 'Polygon':
				symdiffindfeat = ShapelyHelper.export_to_JSON(self.symdifference)
				tmpf = {'type':'Feature','properties':{'areatype':'yellow'}, 'geometry':json.loads(symdiffindfeat)}
				fc['features'].append(tmpf)
	
		with open(opfile, 'w') as output_evaluation:
			output_evaluation.write(json.dumps(fc))

	def cleanDirectories(self):
		cwd = os.getcwd()

		folders = [os.path.join(cwd,config.settings['workingdirectory'])]
		for folder in folders:
			for the_file in os.listdir(folder):
			    file_path = os.path.join(folder, the_file)
			    try:
			        if os.path.isfile(file_path):
			            os.unlink(file_path)
			        elif os.path.isdir(file_path): shutil.rmtree(file_path)
			    except Exception as e:
			        pass

if __name__ == '__main__':
	
	corinedataurl = config.settings['corinedata']
	systems = config.settings['systems']
	regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

	isURL = re.match(regex, corinedataurl) is not None

	myFileDownloader = DataDownloader()
	if isURL: 
		shapefilelist = myFileDownloader.downloadFiles([corinedataurl])
	else: 
		shapefilelist = myFileDownloader.readFile(corinedataurl)


	myClipper = AOIClipper()

	for curshapefile in shapefilelist:	
		clippedFile = myClipper.clipFile(config.settings['aoibounds'], curshapefile)

	# for system, processchain in config.processchains.iteritems():
	for system in systems: 
		processchain = config.processchains[system]
		print("Processing %s .." % system)
		myEvaluationBuilder = EvaluationBuilder(system)
		for evaluationcolor, corinecodes in processchain.items():
			myEvaluationBuilder.processFile(evaluationcolor,clippedFile,corinecodes)

		# myEvaluationBuilder.dissolveColors()
		myEvaluationBuilder.createSymDifference()
		myEvaluationBuilder.writeEvaluationFile()

	
	# myEvaluationBuilder.cleanDirectories()


