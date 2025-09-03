bl_info = {
	"name": "3Division Exporter",
	"author": "Jan Kerkes",
	"version": (1, 2),
	"blender": (2, 80, 0),
	"location": "File > Export",
	"description": "Export Model to 3Division NMF Mesh file",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Import-Export"}

'''
Usage Notes:


'''

import bpy
from bpy.props import *
import mathutils, math, struct
import os
from os import remove
import time
import bpy_extras
from bpy_extras.io_utils import ExportHelper 
import time
import shutil
import bpy
import bmesh
import mathutils
from datetime import datetime
from datetime import timedelta

start_time = datetime.now()
def timerReset():
	start_time = datetime.now()

def timerMillis():
	dt = datetime.now() - start_time
	ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
	return ms

class Plane:
	def __init__(self):
		self.a = 0.0
		self.b = 0.0
		self.c = 1.0
		self.d = 0.0

class Vertex:
	def __init__(self):
		self.vx = 0.0
		self.vy = 0.0
		self.vz = 0.0
		self.nx = 0.0
		self.ny = 0.0
		self.nz = 0.0
		self.t0x = 0.0
		self.t0y = 0.0
		self.tgx = 1.0
		self.tgy = 0.0
		self.tgz = 0.0
		self.btgx = 0.0
		self.btgy = 0.0
		self.btgz = 1.0
		
		self.bidx0 = 0
		self.bidx1 = 0
		self.bidx2 = 0
		self.bidx3 = 0
		
		self.bw0 = 0.0
		self.bw1 = 0.0
		self.bw2 = 0.0
		self.bw3 = 0.0
	
	def __hash__(self):
		return hash(self.vx + self.vy +self.vz)

	def __eq__(self, other):
			if self.vx != other.vx or self.vy != other.vy or self.vz != other.vz:
				return False
			return (#self.vx == other.vx and self.vy == other.vy and self.vz == other.vz and
				
				#((self.nx - other.nx)*(self.nx - other.nx) + (self.ny - other.ny)*(self.ny - other.ny) + (self.nz - other.nz)*(self.nz - other.nz)) < 0.05 and
				#((self.tgx - other.tgx)*(self.tgx - other.tgx) + (self.tgy - other.tgy)*(self.tgy - other.tgy) + (self.tgz - other.tgz)*(self.tgz - other.tgz)) < 0.25 and
				#((self.btgx - other.btgx)*(self.btgx - other.btgx) + (self.btgy - other.btgy)*(self.btgy - other.btgy) + (self.btgz - other.btgz)*(self.btgz - other.btgz)) < 0.25 and
				self.nx == other.nx and self.ny == other.ny and self.nz == other.nz and	
				self.tgx == other.tgx and self.tgy == other.tgy and self.tgz == other.tgz and
				self.btgx == other.btgx and self.btgy == other.btgy and self.btgz == other.btgz and
				self.t0x == other.t0x and self.t0y == other.t0y and
				self.bidx0 == other.bidx0 and self.bidx1 == other.bidx1 and self.bidx2 == other.bidx2 and self.bidx3 == other.bidx3)
	
	def normalizeInfluences(self):
		if self.bw0 > 0.0:
			sum = self.bw0 + self.bw1 + self.bw2 + self.bw3
			invsum = 1.0/sum
			self.bw0 = self.bw0 * invsum
			self.bw1 = self.bw1 * invsum 
			self.bw2 = self.bw2 * invsum 
			self.bw3 = self.bw3 * invsum
		return
		
	def sortInfluences(self):
		if self.bw0 > 0.0:
			# sort influences to have highest first
			for i in range(3):
				if self.bw0 < self.bw1:
					tempw = self.bw0
					tempi = self.bidx0
					self.bw0 = self.bw1
					self.bidx0 = self.bidx1
					self.bw1 = tempw
					self.bidx1 = tempi
				
				if self.bw1 < self.bw2:
					tempw = self.bw1
					tempi = self.bidx1
					self.bw1 = self.bw2
					self.bidx1 = self.bidx2
					self.bw2 = tempw
					self.bidx2 = tempi
					
				if self.bw2 < self.bw3:
					tempw = self.bw2
					tempi = self.bidx2
					self.bw2 = self.bw3
					self.bidx2 = self.bidx3
					self.bw3 = tempw
					self.bidx3 = tempi
				
			
		return 
		
	def addInfluence(self, index, weight):
		# at first find empty one
		lowestOneWeight = self.bw0
		lowestOneIndex = 0
		
		if weight <= 0.0:
			return
			
		if self.bw0 == 0.0:
			self.bw0 = weight
			self.bidx0 = index;
			return
	
		if self.bw1 == 0.0:
			self.bw1 = weight
			self.bidx1 = index;
			return
		elif lowestOneWeight > self.bw1:
			lowestOneWeight = self.bw1
			lowestOneIndex = 1
			
		if self.bw2 == 0.0:
			self.bw2 = weight
			self.bidx2 = index;
			return
		elif lowestOneWeight > self.bw2:
			lowestOneWeight = self.bw2
			lowestOneIndex = 2
			
		if self.bw3 == 0.0:
			self.bw3 = weight
			self.bidx3 = index;
			return
		elif lowestOneWeight > self.bw3:
			lowestOneWeight = self.bw3
			lowestOneIndex = 3
		
		# if all are nonempty, then choose lowest one
		if lowestOneIndex == 0:
			self.bw0 = weight
			self.bidx0 = index;
			return
		if lowestOneIndex == 1:
			self.bw1 = weight
			self.bidx1 = index;
			return
		if lowestOneIndex == 2:
			self.bw2 = weight
			self.bidx2 = index;
			return
		if lowestOneIndex == 3:
			self.bw3 = weight
			self.bidx3 = index;
			return

class ExtractedHelper:
	def __init__(self):
		self.worldMatrix = mathutils.Matrix()
		self.localMatrix = mathutils.Matrix()
		self.name = bytearray()
		self.parent = None
		self.AABB = []

class ExtractedBone:
	def __init__(self):
		self.worldMatrix = mathutils.Matrix()
		self.localMatrix = mathutils.Matrix()
		self.offsetMatrix = mathutils.Matrix()
		self.name = bytearray()
		self.parent = None
		self.globalNodeId = 0
		self.globalNodeParentId = -1
		self.numChilds = 0
		self.AABB = []
		
	def updateAABB(self, point):
		v = self.offsetMatrix @ point
		
		if len(self.AABB) == 0:
			self.AABB.append(v);
			self.AABB.append(v);
		else:
			min = self.AABB[0]
			max = self.AABB[1]
			# find min.x
			if v.x < min.x:
				min.x = v.x
			# find min.y
			if v.y < min.y:
				min.y = v.y
			# find min.z
			if v.z < min.z:
				min.z = v.z
				
			# find max.x
			if v.x > max.x:
				max.x = v.x
			# find max.y
			if v.y > max.y:
				max.y = v.y
			# find max.z
			if v.z > max.z:
				max.z = v.z
			
			self.AABB[0] = min
			self.AABB[1] = max

class ExtractedModel:
	def __init__(self):
		self.vertexList = []
		self.vertexListOptimized = []
		self.vertexListIndices = []
		self.facePlanes = []
		self.AABB = []
		self.faceAABBs = []
		self.materials = []
		self.worldMatrix = mathutils.Matrix()
		self.localMatrix = mathutils.Matrix()
		self.name = bytearray()
		self.attributes = 1
		self.vertexSize = 3 * 4
		self.subsetStarts = []
		self.subsetLasts = []
		self.subsetNumIndices = []
		self.subsetMaterials=[]
		self.subsetGlobalBoneIds = []
		self.parent = None
		self.sizeOfLOD = 0
		self.sizeOfModel = 0
		self.bones = []
	
	def splitSubsets(self, debugFile, maxBones):
		# self.subsetStarts - start index of face
		# self.subsetLasts - end index of face
		doSplit = 1
		#maxBones = 72
		
		while doSplit == 1:
			splitIndex = 0
			newSubsetStart = 0
			newSubsetEnd = 0
			newSubsetBoneList = []
			
			doSplit = 0
			
			for subsetStart, subsetEnd, subsetBonesList in zip(self.subsetStarts, self.subsetLasts, self.subsetGlobalBoneIds):
				vlist = [None] * 3
				# we have start and last index of face
				#debugFile.write( 'splitSubsets startFace {:d} endFace {:d} bones {:d}\n'.format(subsetStart, subsetEnd, len(subsetBonesList)) )
				
				if len(subsetBonesList) > maxBones:
					# iterate subset faces
					for face in range(subsetStart, subsetEnd):
						# construct list of vertices
						vlist[0] = self.vertexList[face * 3 + 0]
						vlist[1] = self.vertexList[face * 3 + 1]
						vlist[2] = self.vertexList[face * 3 + 2]
						
						newBones = []
							
						# look how many bones we need to add, to cover this face
						numberBonesToAdd = 0	
						vbids = [None] * 4
						for v in vlist:
							vbids[0] = subsetBonesList[v.bidx0]
							vbids[1] = subsetBonesList[v.bidx1]
							vbids[2] = subsetBonesList[v.bidx2]
							vbids[3] = subsetBonesList[v.bidx3]
							
							for i in range(4):
								if vbids[i] not in newSubsetBoneList:
									if vbids[i] not in newBones:
										newBones.append(vbids[i])
										
						# are we safe to add them?
						if len(newSubsetBoneList) + len(newBones) <= maxBones:
							# we are fine
							for v in vlist:
								vbid0 = subsetBonesList[v.bidx0]
								vbid1 = subsetBonesList[v.bidx1]
								vbid2 = subsetBonesList[v.bidx2]
								vbid3 = subsetBonesList[v.bidx3]
							
								if vbid0 not in newSubsetBoneList:
									newSubsetBoneList.append(vbid0)
								v.bidx0 = newSubsetBoneList.index(vbid0)
								if vbid1 not in newSubsetBoneList:
									newSubsetBoneList.append(vbid1)
								v.bidx1 = newSubsetBoneList.index(vbid1)
								if vbid2 not in newSubsetBoneList:
									newSubsetBoneList.append(vbid2)
								v.bidx2 = newSubsetBoneList.index(vbid2)
								if vbid3 not in newSubsetBoneList:
									newSubsetBoneList.append(vbid3)
								v.bidx3 = newSubsetBoneList.index(vbid3)
						# no? we need to generate a new subset now
						else:
							splitIndex = self.subsetStarts.index(subsetStart);
							newSubsetStart = subsetStart
							newSubsetEnd = face
							doSplit = 1
							break
					# we get thru all subset and found that it's no longer needed to split it - finalise	
					if doSplit == 0:
						debugFile.write( 'finalising subset to have remainder of {:d} bones\n'.format(len(newSubsetBoneList)))
						index = self.subsetStarts.index(subsetStart);
						self.subsetGlobalBoneIds[index] = newSubsetBoneList
			
						
			if doSplit == 1:
				debugFile.write( 'creating new subset at {:d} startFace {:d} endFace {:d} bones {:d}\n'.format(splitIndex, newSubsetStart, newSubsetEnd, len(newSubsetBoneList)) )
				
				self.subsetStarts.insert(splitIndex, newSubsetStart)
				self.subsetLasts.insert(splitIndex, newSubsetEnd)
				self.subsetGlobalBoneIds.insert(splitIndex, newSubsetBoneList)
				self.subsetMaterials.insert(splitIndex, self.subsetMaterials[splitIndex])
				self.subsetNumIndices.insert(splitIndex, (self.subsetLasts[splitIndex] - self.subsetStarts[splitIndex]) * 3 )
				self.subsetStarts[splitIndex+1] = self.subsetLasts[splitIndex]
				self.subsetNumIndices[splitIndex+1] = self.subsetNumIndices[splitIndex+1] - self.subsetNumIndices[splitIndex]
			
					
	def normalizeInfluences(self):
		for v in self.vertexListOptimized:
			v.normalizeInfluences()
	
	def sortVertexInfluences(self):
		for v in self.vertexList:
			v.sortInfluences()
	
	def sortFacesByInfluences(self):
		for subsetStart, subsetEnd in zip(self.subsetStarts, self.subsetLasts):
			# constrct dictionary of lists that has same bone index on first vertex of face
			
			subsetVertexDictionarySorted = {}
			for face in range(subsetStart, subsetEnd):
				v1 = self.vertexList[face * 3 + 0]
				v2 = self.vertexList[face * 3 + 1]
				v3 = self.vertexList[face * 3 + 2]
				
				if v1.bidx0 not in subsetVertexDictionarySorted:
					localList = []
					localList.append(v1)
					localList.append(v2)
					localList.append(v3)
					subsetVertexDictionarySorted[v1.bidx0] = localList
				else:
					localList = subsetVertexDictionarySorted[v1.bidx0]
					localList.append(v1)
					localList.append(v2)
					localList.append(v3)
			# dump sorted data back to list
			i = subsetStart * 3
			for key in subsetVertexDictionarySorted:
				list = subsetVertexDictionarySorted[key]
				for v in list:
					self.vertexList[i] = v
					i = i + 1
		
		return
		
	def optimize(self):
		# optimize/indexate
		i = 0
		
		# this is there just for optimisation
		vertexDictionary = {}
		
		for v in self.vertexList:
			if v not in vertexDictionary:
				self.vertexListOptimized.append(v)
				self.vertexListIndices.append(i)
				vertexDictionary[v] = i
				i += 1
			else:
				j = vertexDictionary[v]
				self.vertexListIndices.append(j)
				
	def calculateAABB(self):
		min = mathutils.Vector((self.vertexList[0].vx, self.vertexList[0].vy, self.vertexList[0].vz))
		max = mathutils.Vector((self.vertexList[0].vx, self.vertexList[0].vy, self.vertexList[0].vz))
		
		for v in self.vertexList:
			# find min.x
			if v.vx < min.x:
				min.x = v.vx
			# find min.y
			if v.vy < min.y:
				min.y = v.vy
			# find min.z
			if v.vz < min.z:
				min.z = v.vz
				
			# find max.x
			if v.vx > max.x:
				max.x = v.vx
			# find max.y
			if v.vy > max.y:
				max.y = v.vy
			# find max.z
			if v.vz > max.z:
				max.z = v.vz
			
		self.AABB.append(min)
		self.AABB.append(max)
	
	def calculateFacePlanes(self):
		# calculate face planes
		# for v in vertexList
		# v1 =p2-p0 v2 p1-p0 n=v1^v2 normalize d = -n dot p0
		i = 0
		p0 = p1 = p2 = mathutils.Vector((0.0, 0.0, 0.0))
		for v in self.vertexList:
			if (i % 3) == 0:
				p0 = mathutils.Vector((v.vx, v.vy, v.vz))
			if (i % 3) == 1:
				p1 = mathutils.Vector((v.vx, v.vy, v.vz))
			if (i % 3) == 2:
				p2 = mathutils.Vector((v.vx, v.vy, v.vz))
				u1 = p2 -p0
				u2 = p1 -p0
				n = u1.cross( u2)
				n.normalize()
				d = -n.dot( p0)
				p = Plane()
				p.a = n.x
				p.b = n.y
				p.c = n.z
				p.d = d
				self.facePlanes.append(p)
				
				min = p0.copy()
				max = p0.copy()
				
				# find min.x
				if p1.x < min.x:
					min.x = p1.x
				if p2.x < min.x:
					min.x = p2.x
				# find min.y
				if p1.y < min.y:
					min.y = p1.y
				if p2.y < min.y:
					min.y = p2.y
				# find min.z
				if p1.z < min.z:
					min.z = p1.z
				if p2.z < min.z:
					min.z = p2.z
					
				# find max.x
				if p1.x > max.x:
					max.x = p1.x
				if p2.x > max.x:
					max.x = p2.x
				# find max.y
				if p1.y > max.y:
					max.y = p1.y
				if p2.y > max.y:
					max.y = p2.y
				# find max.z
				if p1.z > max.z:
					max.z = p1.z
				if p2.z > max.z:
					max.z = p2.z
				
				self.faceAABBs.append(min)
				self.faceAABBs.append(max)
			i+=1
		
# purpose is to copy the original object, as we are about to call modifying operations on it
# after export it will be removed
def copyAndTriangulateNMesh(debugFile, object):
	bneedtri = False
	scene = bpy.context.scene
	for i in scene.objects: i.select_set(False) #deselect all objects
	object.select_set(True)
	
	bpy.context.view_layer.objects.active = object #set the mesh object to current
	bpy.ops.object.mode_set(mode='OBJECT')
	debugFile.write( 'Checking mesh if needs to convert quad to Tri...\n')
	# object.data.update(calc_edges=True, calc_edges_loose=True)
	
	for poly in object.data.polygons:
		# loop over vertices in triangle
		if poly.loop_total > 3:
			bneedtri = True
			break
			
	
	bpy.ops.object.mode_set(mode='OBJECT')
	
	if bneedtri == True:
		me_da = object.data.copy() #copy data
		me_ob = object.copy() #copy object
		#note two copy two types else it will use the current data or mesh
		me_ob.data = me_da
		
		debugFile.write( 'Converting quad to tri mesh...\n')
		# force triangulation on mesh
		bm = bmesh.new()
		bm.from_mesh(me_ob.data)
		bmesh.ops.triangulate(bm, faces=bm.faces[:])
		bm.to_mesh(me_ob.data)
		bm.free()
		
		bpy.context.scene.collection.objects.link(me_ob)#link the object to the scene #current object location
		bpy.context.view_layer.update()
	else:
		me_da = object.data.copy() #copy data
		me_ob = object.copy() #copy object
		#note two copy two types else it will use the current data or mesh
		me_ob.data = me_da
		bpy.context.scene.collection.objects.link(me_ob)#link the object to the scene #current object location
		bpy.context.view_layer.update()
		debugFile.write( 'No need to convert tri mesh.\n')
	
	return me_ob

def writeString(file, string):
	file.write(bytes(string, 'UTF-8'))

def buildSortedSubObjects(selobjs_filtered, parent, parentindex, parents, selobjs_sorted):
	# find childs of parent
	for obindex, ob in enumerate(selobjs_filtered):
		# if parent index array indicates that parent of current object is caller, append and recursively extract childs
		if parents[obindex] == parentindex:
			selobjs_sorted.append(ob)
			buildSortedSubObjects(selobjs_filtered, ob, obindex, parents, selobjs_sorted)

def do_export_anim(context, props, filepath):
	timerReset()
	# open files for writing
	debugFile = open(filepath + "debug", "wt")
	debugFile.write( 'start {:d}\n'.format(int(timerMillis())) )
	
	# construct rotation matrix -90* around X axis
	mat_x90 = mathutils.Matrix.Rotation(-math.pi/2, 4, 'X')
	# keep it as it is, not do any rotation
	#mat_x90.identity()
	# construct inverse transform to above
	mat_x90inv = mat_x90.copy()
	mat_x90inv.invert()
	
	# get list of selected objects from scene
	current_scene = context.scene
	selobjs_all = context.selected_objects.copy()
	
	# filter out what we are not interested in
	selobjs_filtered = []
	for obindex, ob in enumerate(selobjs_all):
		if ob.type == 'MESH':
			selobjs_filtered.append(ob)
	
	bones = []
	boneNames = []
	boneArmatures = []
	
	startFrame = props.animation_startFrame
	endFrame = props.animation_endFrame
	
	debugFile.write( 'startFrame {:d}, endFrame {:d}\n'.format(startFrame, endFrame) )
	
	# loop over objects and extract bones
	for obindex, ob in enumerate(selobjs_filtered):
		# get armature of object
		armature = None
		object_bones = None
		object_bone_names = None
		tempob = ob
		
		# get object armature way #1
		#while tempob.parent != None:
		#	tempob = tempob.parent
		#	if tempob.type == 'ARMATURE':
		#		armature = tempob
				
		# get object armature way #2
		for modifier in tempob.modifiers:
			if modifier.type == 'ARMATURE':
				armature = modifier.object
		
		# get list of bone names
		if armature != None:
			armature_bones = armature.pose.bones
			armature_bind_bones = armature.data.bones
			
			armature_bone_names = [b.name for b in armature_bones]
			armature_bind_bone_names = [b.name for b in armature_bones]
			
			debugFile.write("Object bones\n")
			debugFile.write(str(armature_bone_names))
			
			# here we make sure, the order of bones in anim file, is the same like order of bones in mesh file
			for bind_bone in armature_bind_bones:
				for bone in armature_bones:
					if bind_bone.name == bone.name:
						if bone.name not in boneNames:
							boneNames.append(bone.name)
							bones.append(bone)
							boneArmatures.append(armature)
			
			#for bone in armature_bones:
			#	if bone.name not in boneNames:
			#		boneNames.append(bone.name)
			#		bones.append(bone)
			#		boneArmatures.append(armature)
	
	# now we have all bones, write animation_endFrame
	file = open(filepath, "wb") 
	
	# write first 4 bytes of header
	file.write(struct.pack("<cccc", b'B', b'3', b'D', b'A'))
	# write next 4 bytes of header
	file.write(struct.pack("<cccc", b'M', b'\0', b'1', b'0'))
	# format - 0
	file.write(struct.pack("<L", 0))
	# write num nodes	
	file.write(struct.pack("<L", len(bones)))
	# fps
	file.write(struct.pack("<L", 30 ))
	# spf
	file.write(struct.pack("<L", 1))
	# num frames
	file.write(struct.pack("<L", endFrame - startFrame + 1))
	# size
	file.write(struct.pack("<L", 0))
	
	boneAnimMatricesArrays = []
	
	# construct list of matrices per each bone
	for bone in bones:
		emptyList = []
		boneAnimMatricesArrays.append(emptyList)
	
	# for every frame
	for i in range(startFrame, endFrame + 1):
		bpy.context.scene.frame_set(i)
		# for every bone
		for bone, armature, matrixArray in zip(bones, boneArmatures, boneAnimMatricesArrays):
			# extract world matrix and extend bone array
			worldMatrix = mat_x90 @ armature.matrix_world @ bone.matrix
			#worldMatrix = mat_x90 @ armature.matrix_world @ bone.matrix_local
			matrixArray.append(worldMatrix.copy())
		
	# write every bone
	for bone, matrixArray in zip(bones, boneAnimMatricesArrays):
		# bone name
		b = bytearray()
		b.extend(bytes(bone.name, 'UTF-8'))
		b += b'\0'*(64-len(b))
		file.write(b)
		# write matrices of bones
		for worldMatrix in matrixArray:
			# write transform - world one
			file.write(struct.pack("<ffff", worldMatrix[0][0], worldMatrix[1][0], worldMatrix[2][0], worldMatrix[3][0]))
			file.write(struct.pack("<ffff", worldMatrix[0][1], worldMatrix[1][1], worldMatrix[2][1], worldMatrix[3][1]))
			file.write(struct.pack("<ffff", worldMatrix[0][2], worldMatrix[1][2], worldMatrix[2][2], worldMatrix[3][2]))
			file.write(struct.pack("<ffff", worldMatrix[0][3], worldMatrix[1][3], worldMatrix[2][3], worldMatrix[3][3]))
	
	debugFile.flush()
	debugFile.close()
	
	file.flush()
	file.close()

	return True

	

def do_export(context, props, filepath):
	
	timerReset()
	# open files for writing
	debugFile = open(filepath + "debug", "wt")
	debugFile.write( 'start {:d}\n'.format(int(timerMillis())) )
	
	# construct rotation matrix -90* around X axis
	mat_x90 = mathutils.Matrix.Rotation(-math.pi/2, 4, 'X')
	# keep it as it is, not do any rotation
	#mat_x90.identity()
	# construct inverse transform to above
	mat_x90inv = mat_x90.copy()
	mat_x90inv.invert()
	
	# get list of selected objects from scene
	current_scene = context.scene
	apply_modifiers = props.apply_modifiers
	selobjs_all = context.selected_objects.copy()
	
	maxBones = props.export_maxBones
	
	# filter out what we are not interested in
	selobjs_filtered = []
	for obindex, ob in enumerate(selobjs_all):
		if ob.type == 'MESH':
			selobjs_filtered.append(ob)
	
	# two main lists that are output of scene selection data extraction
	materials = []
	models = []
	helpers = []
	bones = []
	boneNames = []
	boneNextId = 0

	# parents
	parents = [-1]*len(selobjs_filtered)
	
	# set parents
	for obindex, ob in enumerate(selobjs_filtered):
		if ob.parent in selobjs_filtered:
			parents[obindex] = selobjs_filtered.index(ob.parent)
	
	debugFile.write( 'objects before sorting\n')
	debugFile.write( str(selobjs_filtered))
	selobjs_sorted = []
	
	# sort list by parents
	for obindex, ob in enumerate(selobjs_filtered):
		if parents[obindex] == -1:
			selobjs_sorted.append(ob)
			buildSortedSubObjects(selobjs_filtered, ob, obindex, parents, selobjs_sorted);
	
	debugFile.write( 'objects after sorting\n')
	debugFile.write( str(selobjs_sorted))
	
	parents = [-1]*len(selobjs_sorted)	
	# set parents again, as the indexes changes
	for obindex, ob in enumerate(selobjs_sorted):
		if ob.parent in selobjs_sorted:
			parents[obindex] = selobjs_sorted.index(ob.parent)
	
	debugFile.write( 'parents after sorting\n')
	debugFile.write( str( parents))
	
	# helpers
	for obindex, ob in enumerate(selobjs_all):
		if ob.type == 'EMPTY':
			helper = ExtractedHelper()
			# prepare matrices
			helper.worldMatrix = mat_x90 @ mathutils.Matrix(ob.matrix_world)
			helper.name = bytearray()
			helper.name.extend(bytes(ob.name, 'UTF-8'))
			helper.name += b'\0'*(64-len(ob.name))
			size = ob.empty_display_size * 0.5
			helper.AABB.append(mathutils.Vector((-size, -size, -size)))
			helper.AABB.append(mathutils.Vector((size, size, size)))
			helpers.append(helper)
	
	
	# loop over objects and extract them
	for obindex, ob in enumerate(selobjs_sorted):
		if ob.type == 'MESH':
			model = ExtractedModel()
			# prepare matrices
			worldMatrix = mathutils.Matrix(ob.matrix_world)
		
			finalMatrixToApply = mathutils.Matrix()
			finalMatrixToWrite = mathutils.Matrix()
		
			# export as root node
			if parents[obindex] == -1:
				# export in world space
				finalMatrixToApply = mat_x90 @ worldMatrix # * vertex
			
				#model.worldMatrix = finalMatrixToApply.copy()
				model.worldMatrix = mathutils.Matrix()
				model.localMatrix = mathutils.Matrix()
			# export as child node
			else:
				# export in world space
				finalMatrixToApply = mat_x90 @ worldMatrix # * vertex
			
				#model.worldMatrix = finalMatrixToApply.copy()
				model.worldMatrix = mathutils.Matrix()
				model.localMatrix = mathutils.Matrix()
			
			# extract model name - 64 bytes
			model.name = bytearray()
			model.name.extend(bytes(ob.name, 'UTF-8'))
			model.name += b'\0'*(64-len(ob.name))
			
			# do local copy of mesh - we need to execute some actions on it like transformation, triangulation and so
			me_ob = copyAndTriangulateNMesh(debugFile, ob)
			mesh = me_ob.to_mesh(depsgraph=bpy.context.evaluated_depsgraph_get(), preserve_all_data_layers=True)
			mesh.transform(finalMatrixToApply)
			
			# mesh.update(calc_edges=True, calc_edges_loose=True)
			
			#mesh.calc_normals_split()
			#uv_layer = mesh.uv_layers.get("XY")
			#uv_layer = mesh.uv_layers.active 
			uv_layer = mesh.uv_layers.active
			if uv_layer != None:
				mesh.calc_tangents()
                
			uv_layer = mesh.uv_layers.active
			
			# get armature of object
			armature = None
			object_bones = None
			object_bone_names = None
			tempob = ob
							
			# get object armature way #1
			#while tempob.parent != None:
			#	tempob = tempob.parent
			#	if tempob.type == 'ARMATURE':
			#		armature = tempob
					
			# get object armature way #2
			for modifier in tempob.modifiers:
				if modifier.type == 'ARMATURE':
					armature = modifier.object
						
			# get list of bone names
			if armature != None:
				armature_bones = armature.data.bones
				armature_bone_names = [b.name for b in armature_bones]
				debugFile.write("Object bones\n")
				debugFile.write(str(armature_bone_names))
				
				# for each bone in armature
				for bone in armature_bones:
					# check if we already exported it as part of other mesh
					if bone.name not in boneNames:
						# if not, create record of new bone to export
						extractedBone = ExtractedBone()	
						extractedBone.name = bytearray()
						extractedBone.name.extend(bytes(bone.name, 'UTF-8'))
						extractedBone.name += b'\0'*(64-len(bone.name))
						extractedBone.worldMatrix = mat_x90 @ armature.matrix_world @ bone.matrix_local
						extractedBone.globalNodeId = boneNextId
						
						inverted = extractedBone.worldMatrix.copy()
						inverted.invert()
						
						extractedBone.offsetMatrix = inverted
						
						parentId = -1
						
						# do hierarchy stuff
						if bone.parent != None:
							if bone.parent.name in boneNames:
								parentId = boneNames.index(bone.parent.name)
								extractedBone.parent = bones[parentId]
								bones[parentId].numChilds = bones[parentId].numChilds + 1
								
								parentInverted = bones[parentId].worldMatrix.copy()
								parentInverted.invert()
								
								extractedBone.localMatrix = parentInverted @ extractedBone.worldMatrix
								
						extractedBone.globalNodeParentId = parentId
						debugFile.write( 'bone {:s} with id {:d} has parent {:d}\n'.format(bone.name, boneNextId, parentId) )
						
						# store new bone
						boneNextId = boneNextId + 1
						bones.append(extractedBone)
						boneNames.append(bone.name)
			# b.parent, list of bones is sorted, so parent is always before child
			# get bone names that affect this object - vertex group name is same as bone name
			object_groups = me_ob.vertex_groups
			object_group_names = [g.name for g in object_groups]
			
			# get list of bones that affect just this mesh, ignore other bones of skeleton
			object_bones = []
			if armature != None:
				for bone in armature_bones:
					# ignore bones of whole armature, that are not affecting this object
					if bone.name in object_group_names:
						object_bones.append(bone)
				
			groupIndexToExtractedBonedictionary = {}
			
			# create dictionary that maps group index g.group, to bone
			for bone in object_bones:
				vertex_group_of_a_bone = object_groups[bone.name]
				vertex_group_index_of_a_bone = vertex_group_of_a_bone.index
				extractedBoneId = boneNames.index(bone.name)
				extractedBone = bones[extractedBoneId]
				groupIndexToExtractedBonedictionary[vertex_group_index_of_a_bone] = extractedBone
				
			debugFile.write("Vertex groups names\n")
			debugFile.write(str(object_group_names))
			
			# extract vertex attributes
			model.attributes = 1
			model.vertexSize = 3 * 4
			
			if props.export_0uvset:
				model.attributes = model.attributes | (1 << 8)
				model.vertexSize += 2 * 4
#			if props.export_1uvset
#				model.attributes = model.attributes | (1 << 9)
#				model.vertexSize += 2 * 4
			if props.export_normals:
				model.attributes = model.attributes | (1 << 3)
				model.vertexSize += 3 * 4
			if props.export_tangents:
				model.attributes = model.attributes | (1 << 4)
				model.vertexSize += 3 * 4
			if props.export_bitangents:
				model.attributes = model.attributes | (1 << 5)
				model.vertexSize += 3 * 4
#			if props.export_colors
#				attributes = attributes | (1 << 2)
			if props.export_faceplanes:
				model.attributes = model.attributes | (1 << 18)
				
			if armature != None:
				model.attributes = model.attributes | (1 << 16)
				model.vertexSize += 4*2
				model.attributes = model.attributes | (1 << 17)
				model.vertexSize += 4
			
			# all model materials, including unused ones
			modelMaterials = ob.data.materials
			
			# position marked with 0 at i means that material i is used
			modelMaterialsUsageMap = [-1] * len(modelMaterials)
			
			# faces sorted by material
			facesSorted = []
			
			# loop over triangles and check which materials are actually used
			for poly in mesh.polygons:
				# mark material as used
				material_index = poly.material_index
				modelMaterialsUsageMap[material_index] = 0
			
			print('Mesh polygons before attempt to create subsets')
			print(len(mesh.polygons))
			
			# loop over used materials (subsets) and construct polygons list with subset ranges
			for materialIndex, materialUsedFlag in enumerate(modelMaterialsUsageMap):
				# for used materials
				if materialUsedFlag == 0:
					# make sure we have it in our list
					material = modelMaterials[materialIndex]
					
					if not material in materials:
						materials.append(material)
					# loop over triangles, that uses particular material
					start = len(facesSorted)
					for poly in mesh.polygons:
						if poly.material_index == materialIndex:
							facesSorted.append(poly)
					numIndices = (len(facesSorted) - start)*3
					
					print('model.subsetStarts.append(start)')
					print(str(start))
					
					model.subsetStarts.append(start)
					
					print('model.subsetLasts.append(start + len(facesSorted))')
					print(str(len(facesSorted)))
					
					#model.subsetLasts.append(start + len(facesSorted))
					model.subsetLasts.append(len(facesSorted))
					model.subsetNumIndices.append(numIndices)
					model.subsetMaterials.append(materials.index(material))
					
			for start,end in zip(model.subsetStarts, model.subsetLasts):
				# bones of subset
				subsetGlobalBoneIdsDictionary = {}
				subsetGlobalBoneIds = []
				for poly in facesSorted[start: end]:
					for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
						v = Vertex()
						
						model_vertex_index = mesh.loops[loop_index].vertex_index
						
						vertex = mesh.vertices[model_vertex_index].co
						normal = mathutils.Vector(mesh.loops[loop_index].normal)
						
						tangent = mathutils.Vector(mesh.loops[loop_index].tangent)
						bitangent = mathutils.Vector(mesh.loops[loop_index].bitangent)
						
						
						#normal.normalize()
						#tangent.normalize()
						#bitangent.normalize()
						
						if uv_layer != None:
							uv =  uv_layer.uv[loop_index].vector
						else:
							uv = [0.0, 0.0]
                            
						#uv_value = uv_layer.uv[loop_index].vector
						#print("    UV: {!r}".format(uv_value.x, uv_value.y))
						#print("    UV: {!r}".format(uv_layer.uv[loop_index]))
						#print(uv[1])
						
						v.vx = vertex.x
						v.vy = vertex.y
						v.vz = vertex.z
						v.nx = normal[0]
						v.ny = normal[1]
						v.nz = normal[2]
						# v.uv = uv
						v.t0x = uv[0]
						v.t0y = 1.0 - uv[1]
						
						# put minus there to invert X axis on normal map
						v.tgx = tangent[0]
						v.tgy = tangent[1]
						v.tgz = tangent[2]
						
						v.btgx = bitangent[0]
						v.btgy = bitangent[1]
						v.btgz = bitangent[2]
						
						# vertex groups list that this vertex belongs to
						this_vertex_groups = mesh.vertices[model_vertex_index].groups
							
						# so if a bone affects this vertex
						for g in this_vertex_groups:
							# only add bone if it really affects
							weight = g.weight
							if weight > 0.05:
								# lookup bone, that belongs to this vertex group
								if g.group in groupIndexToExtractedBonedictionary:
									extractedBone = groupIndexToExtractedBonedictionary[g.group]
									extractedBoneGlobalId = extractedBone.globalNodeId
										
									if extractedBoneGlobalId not in subsetGlobalBoneIdsDictionary:
										subsetGlobalBoneIdsDictionary[extractedBoneGlobalId] = len(subsetGlobalBoneIds)
										subsetGlobalBoneIds.append(extractedBoneGlobalId)
									index = subsetGlobalBoneIdsDictionary[extractedBoneGlobalId]
									
									# add weight and index as a vertex influence
									v.addInfluence(index, weight)
									
									# update bounding box of a bone
									if weight > 0.25:
										extractedBone.updateAABB(vertex)				
								
						model.vertexList.append(v)
				
				model.subsetGlobalBoneIds.append(subsetGlobalBoneIds)
			
			print('Number of vertices before optimization')
			print(len(model.vertexList))
			
			print('Number of polygons on mesh')
			print(len(mesh.polygons))
			
			#debugFile.write('Vertex list')
			#debugFile.write(str(model.vertexList))
			
			print('Model subsetStarts')
			print(str(model.subsetStarts))
			
			print('Model subsetLasts')
			print(str(model.subsetLasts))
			
			#mesh.free_normals_split()
			bpy.data.objects.remove(me_ob)
			
			model.sortVertexInfluences()
			model.sortFacesByInfluences()
			model.splitSubsets(debugFile, maxBones)
			model.optimize()
			model.calculateFacePlanes()
			model.calculateAABB()
			model.normalizeInfluences()
			
			models.append(model)
	
	sizeTotal = 4+4+4+4+4
	
	# calculate model sizes
	for model in models:
		# calculate mesh LOD size
		sizeOfLOD = 28 # header
		sizeOfLOD += model.vertexSize * len(model.vertexListOptimized) # vertex data
		sizeOfLOD += 2 * len(model.vertexListIndices) # index data
		if props.export_faceplanes:
			sizeOfLOD += (4+3+3) * 4 * (len(model.vertexListIndices)//3) # faceplanes aabbs
		sizeOfLOD += (4+4+2+2) * len(model.subsetStarts) # subset data
		
		sizeOfModel = 4+4+64+2+2+64+64+24+4 + sizeOfLOD
		
		model.sizeOfLOD = sizeOfLOD
		model.sizeOfModel = sizeOfModel
		sizeTotal += sizeOfModel
		
	# calculate material sizes
	sizeTotal += len(materials)*64
	
	# calculate helpers sizes
	helperStructSize = 4+4+64+2+2+64+64+24+64
	sizeTotal += len(helpers)*helperStructSize
	
	# calculate bones size
	boneStructSize = 4+4+64+2+2+64+64+24+64
	sizeTotal += len(bones)*boneStructSize
	
	# open files for writing
	file = open(filepath, "wb") 
	
	# write first 4 bytes of header
	file.write(struct.pack("<cccc", b'B', b'3', b'D', b'M'))
	# write next 4 bytes of header
	file.write(struct.pack("<cccc", b'H', b'\0', b'1', b'0'))
	# write num materials
	file.write(struct.pack("<L", len(materials)))
	# write num nodes
	file.write(struct.pack("<L", len(selobjs_filtered)+len(bones)+len(helpers)))
	# write size
	file.write(struct.pack("<L", sizeTotal))
	
	# writing material names
	for material in materials:
		b = bytearray()
		if material is not None:
			material_name = material.name
		else:
			material_name = 'DefaultMaterialName'  # Replace with your desired default name
		b.extend(bytes(material_name, 'UTF-8'))
		b += b'\0'*(64-len(b))
		file.write(b)
	
	for bone in bones:		
		# write node type - 1 for bone
		file.write(struct.pack("<L", 1))
		# write size
		file.write(struct.pack("<L", boneStructSize))
		# write model name
		file.write(bone.name)
		
		# write parent ID
		file.write(struct.pack("<h", bone.globalNodeParentId))
		# write num childs
		file.write(struct.pack("<h", bone.numChilds))
		
		# write transform - world one
		file.write(struct.pack("<ffff", bone.worldMatrix[0][0], bone.worldMatrix[1][0], bone.worldMatrix[2][0], bone.worldMatrix[3][0]))
		file.write(struct.pack("<ffff", bone.worldMatrix[0][1], bone.worldMatrix[1][1], bone.worldMatrix[2][1], bone.worldMatrix[3][1]))
		file.write(struct.pack("<ffff", bone.worldMatrix[0][2], bone.worldMatrix[1][2], bone.worldMatrix[2][2], bone.worldMatrix[3][2]))
		file.write(struct.pack("<ffff", bone.worldMatrix[0][3], bone.worldMatrix[1][3], bone.worldMatrix[2][3], bone.worldMatrix[3][3]))
		
		# write transform - local one
		file.write(struct.pack("<ffff", bone.localMatrix[0][0], bone.localMatrix[1][0], bone.localMatrix[2][0], bone.localMatrix[3][0]))
		file.write(struct.pack("<ffff", bone.localMatrix[0][1], bone.localMatrix[1][1], bone.localMatrix[2][1], bone.localMatrix[3][1]))
		file.write(struct.pack("<ffff", bone.localMatrix[0][2], bone.localMatrix[1][2], bone.localMatrix[2][2], bone.localMatrix[3][2]))
		file.write(struct.pack("<ffff", bone.localMatrix[0][3], bone.localMatrix[1][3], bone.localMatrix[2][3], bone.localMatrix[3][3]))
		
		# write AABB min
		# write AABB max
		if len(bone.AABB) == 2:
			file.write(struct.pack("<fff", bone.AABB[0].x, bone.AABB[0].y, bone.AABB[0].z))
			file.write(struct.pack("<fff", bone.AABB[1].x, bone.AABB[1].y, bone.AABB[1].z))
		else:
			file.write(struct.pack("<fff", 0.0, 0.0, 0.0))
			file.write(struct.pack("<fff", 0.0, 0.0, 0.0))
		
		
		# write transform - offset one
		file.write(struct.pack("<ffff", bone.offsetMatrix[0][0], bone.offsetMatrix[1][0], bone.offsetMatrix[2][0], bone.offsetMatrix[3][0]))
		file.write(struct.pack("<ffff", bone.offsetMatrix[0][1], bone.offsetMatrix[1][1], bone.offsetMatrix[2][1], bone.offsetMatrix[3][1]))
		file.write(struct.pack("<ffff", bone.offsetMatrix[0][2], bone.offsetMatrix[1][2], bone.offsetMatrix[2][2], bone.offsetMatrix[3][2]))
		file.write(struct.pack("<ffff", bone.offsetMatrix[0][3], bone.offsetMatrix[1][3], bone.offsetMatrix[2][3], bone.offsetMatrix[3][3]))
		sizeTotal += boneStructSize
	
	for helper in helpers:		
		# write node type - 2 for helper
		file.write(struct.pack("<L", 2))
		# write size
		file.write(struct.pack("<L", helperStructSize))
		# write model name
		file.write(helper.name)
		
		# write parent ID
		file.write(struct.pack("<h", -1))
		# write num childs
		file.write(struct.pack("<h", 0))
		
		# write transform - world one
		file.write(struct.pack("<ffff", helper.worldMatrix[0][0], helper.worldMatrix[1][0], helper.worldMatrix[2][0], helper.worldMatrix[3][0]))
		file.write(struct.pack("<ffff", helper.worldMatrix[0][1], helper.worldMatrix[1][1], helper.worldMatrix[2][1], helper.worldMatrix[3][1]))
		file.write(struct.pack("<ffff", helper.worldMatrix[0][2], helper.worldMatrix[1][2], helper.worldMatrix[2][2], helper.worldMatrix[3][2]))
		file.write(struct.pack("<ffff", helper.worldMatrix[0][3], helper.worldMatrix[1][3], helper.worldMatrix[2][3], helper.worldMatrix[3][3]))
		
		# write transform - local one
		file.write(struct.pack("<ffff", helper.localMatrix[0][0], helper.localMatrix[1][0], helper.localMatrix[2][0], helper.localMatrix[3][0]))
		file.write(struct.pack("<ffff", helper.localMatrix[0][1], helper.localMatrix[1][1], helper.localMatrix[2][1], helper.localMatrix[3][1]))
		file.write(struct.pack("<ffff", helper.localMatrix[0][2], helper.localMatrix[1][2], helper.localMatrix[2][2], helper.localMatrix[3][2]))
		file.write(struct.pack("<ffff", helper.localMatrix[0][3], helper.localMatrix[1][3], helper.localMatrix[2][3], helper.localMatrix[3][3]))
		
		# write AABB min
		# write AABB max
		if len(helper.AABB) == 2:
			file.write(struct.pack("<fff", helper.AABB[0].x, helper.AABB[0].y, helper.AABB[0].z))
			file.write(struct.pack("<fff", helper.AABB[1].x, helper.AABB[1].y, helper.AABB[1].z))
		else:
			file.write(struct.pack("<fff", 0.0, 0.0, 0.0))
			file.write(struct.pack("<fff", 0.0, 0.0, 0.0))
		
		helperInverted = helper.worldMatrix.copy()
		helperInverted.invert()
						
		# write transform - offset one
		file.write(struct.pack("<ffff", helperInverted[0][0], helperInverted[1][0], helperInverted[2][0], helperInverted[3][0]))
		file.write(struct.pack("<ffff", helperInverted[0][1], helperInverted[1][1], helperInverted[2][1], helperInverted[3][1]))
		file.write(struct.pack("<ffff", helperInverted[0][2], helperInverted[1][2], helperInverted[2][2], helperInverted[3][2]))
		file.write(struct.pack("<ffff", helperInverted[0][3], helperInverted[1][3], helperInverted[2][3], helperInverted[3][3]))
					
	
	for model in models:		
		# write node type - 0 for mesh
		file.write(struct.pack("<L", 0))
		# write size
		file.write(struct.pack("<L", model.sizeOfModel))
		# write model name
		file.write(model.name)
		
		# write parent ID
		file.write(struct.pack("<h", -1))
		# write num childs
		file.write(struct.pack("<h", 0))
		
		# write transform - world one
		file.write(struct.pack("<ffff", model.worldMatrix[0][0], model.worldMatrix[1][0], model.worldMatrix[2][0], model.worldMatrix[3][0]))
		file.write(struct.pack("<ffff", model.worldMatrix[0][1], model.worldMatrix[1][1], model.worldMatrix[2][1], model.worldMatrix[3][1]))
		file.write(struct.pack("<ffff", model.worldMatrix[0][2], model.worldMatrix[1][2], model.worldMatrix[2][2], model.worldMatrix[3][2]))
		file.write(struct.pack("<ffff", model.worldMatrix[0][3], model.worldMatrix[1][3], model.worldMatrix[2][3], model.worldMatrix[3][3]))
		
		# write transform - local one
		file.write(struct.pack("<ffff", model.localMatrix[0][0], model.localMatrix[1][0], model.localMatrix[2][0], model.localMatrix[3][0]))
		file.write(struct.pack("<ffff", model.localMatrix[0][1], model.localMatrix[1][1], model.localMatrix[2][1], model.localMatrix[3][1]))
		file.write(struct.pack("<ffff", model.localMatrix[0][2], model.localMatrix[1][2], model.localMatrix[2][2], model.localMatrix[3][2]))
		file.write(struct.pack("<ffff", model.localMatrix[0][3], model.localMatrix[1][3], model.localMatrix[2][3], model.localMatrix[3][3]))
		
		# write AABB min
		# write AABB max
		file.write(struct.pack("<fff", model.AABB[0].x, model.AABB[0].y, model.AABB[0].z))
		file.write(struct.pack("<fff", model.AABB[1].x, model.AABB[1].y, model.AABB[1].z))
		
		# write num lods
		file.write(struct.pack("<L", 1))
		
		# ---- LOD HEADER ------
		debugFile.write( 'vertex count before {:d}\n'.format(len(model.vertexList)) )
		debugFile.write( 'vertex count after {:d}\n'.format(len(model.vertexListOptimized)) )
		
		# write size
		file.write(struct.pack("<L", model.sizeOfLOD))
		# write num vertices
		file.write(struct.pack("<L", len(model.vertexListOptimized)))
		# write num indexes
		file.write(struct.pack("<L", len(model.vertexListIndices)))
		# write num subsets
		file.write(struct.pack("<L", len(model.subsetStarts)))
		# write num morph targets
		file.write(struct.pack("<L", 0))
		# write vertex format attributes
		file.write(struct.pack("<L", model.attributes))
		# write morph mask
		file.write(struct.pack("<L", 0))
        
		print('len(model.vertexListOptimized)')
		print(len(model.vertexListOptimized))
        
		print('len(model.vertexListIndices)')
		print(len(model.vertexListIndices))
        
		print('len(model.subsetStarts)')
		print(len(model.subsetStarts))
		
		# write indexes
		for vi in model.vertexListIndices:
			file.write(struct.pack("<H", vi));
			#writeString(file, '%d\n' % (vi))
		
		# write positions 
		for v in model.vertexListOptimized:
			file.write(struct.pack("<fff", v.vx, v.vy, v.vz));
			#debugFile.write( 'bw {:d} {:d} {:d} {:d}: {:f} {:f} {:f} {:f}\n'.format(v.bidx0, v.bidx1, v.bidx2, v.bidx3, v.bw0, v.bw1, v.bw2, v.bw3) )
		#if props.export_colors:
		#	for v in vertexListOptimized:
		#		file.write(struct.pack("<cccc", b'\xff', b'\xff', b'\xff', b'\xff'));
		if props.export_normals:
			for v in model.vertexListOptimized:
				file.write(struct.pack("<fff", v.nx, v.ny, v.nz));
		if props.export_tangents:
			for v in model.vertexListOptimized:
				file.write(struct.pack("<fff", v.tgx, v.tgy, v.tgz));
		if props.export_bitangents:
			for v in model.vertexListOptimized:
				file.write(struct.pack("<fff", v.btgx, v.btgy, v.btgz));
		if props.export_0uvset:
			for v in model.vertexListOptimized:
				file.write(struct.pack("<ff", v.t0x, v.t0y));
			#writeString(file, '%f, %f, %f\n' % (v.vx, v.vy, v.vz))
		if (model.attributes & (1 << 16)) != 0:
			for v in model.vertexListOptimized:
				file.write(struct.pack("<HHHH", int(v.bw0 * 32767.0), int(v.bw1 * 32767.0), int(v.bw2 * 32767.0), int(v.bw3 * 32767.0)));
			for v in model.vertexListOptimized:
				file.write(struct.pack("<BBBB", v.bidx0, v.bidx1, v.bidx2, v.bidx3));
		
		# write face planes
		if props.export_faceplanes:
			for p in model.facePlanes:
				file.write(struct.pack("<ffff", p.a, p.b, p.c, p.d));	
			for p in model.faceAABBs:
				file.write(struct.pack("<fff", p.x, p.y, p.z));
		#	subset data - start index and num indexes
		for subsetStart, subsetNumIndices, subsetMaterial, subsetGlobalBoneIds in zip(model.subsetStarts, model.subsetNumIndices, model.subsetMaterials, model.subsetGlobalBoneIds):
			debugFile.write( 'subsetStart {:d}\n'.format(subsetStart * 3) )
			debugFile.write( 'subsetCount {:d}\n'.format(subsetNumIndices) )
		
			file.write(struct.pack("<L", subsetStart * 3))
			file.write(struct.pack("<L", subsetNumIndices))
			# write material index for this subset
			file.write(struct.pack("<H", subsetMaterial));
			# write num joints for subset
			debugFile.write( 'subsetBones {:d}\n'.format(len(subsetGlobalBoneIds)) )
			
			file.write(struct.pack("<H", len(subsetGlobalBoneIds)));
			# write joints of this submesh as list of shorts
			for bid in subsetGlobalBoneIds:
				file.write(struct.pack("<H", bid));
		
	
	debugFile.flush()
	debugFile.close()
	
	file.flush()
	file.close()

	return True


###### EXPORT OPERATOR #######
class Export_objc(bpy.types.Operator, ExportHelper):
	'''Exports the active Object as an NMF File.'''
	bl_idname = "export_object.nmf"
	bl_label = "Export NMF File (.nmf)"

	filename_ext = ".nmf"
	
	detect_lods : BoolProperty(name="Detect LODs (_0, _1, ...)",
						description="Detect level of detail meshes",
						default=True)
	
	export_0uvset : BoolProperty(name="Export 0. uvset",
						description="Export texture coordinates - 0th set",
						default=True)
	
	export_1uvset : BoolProperty(name="Export 1. uvset",
						description="Export texture coordinates - 1th set",
						default=False)
						
	export_normals : BoolProperty(name="Export normals",
						description="Export normals",
						default=True)

	export_tangents : BoolProperty(name="Export tangents",
						description="Export tangents",
						default=True)

	export_bitangents : BoolProperty(name="Export bitangents",
						description="Export bitangents",
						default=True)

	export_colors : BoolProperty(name="Export colors",
						description="Export colors",
						default=False)

	export_faceplanes : BoolProperty(name="Export faceplanes/face-aabbs",
						description="Export face plane equations and axis aligned bounding boxes",
						default=True)

						
	apply_modifiers : BoolProperty(name="Apply Modifiers",
							description="Applies the Modifiers",
							default=True)
							
	export_maxBones : bpy.props.IntProperty(name="Max Bones", default = 24)
	
	#world_space = BoolProperty(name="Export into Worldspace",
	#						description="Transform the Vertexcoordinates into Worldspace",
	#						default=False)
							
	#tangents = BoolProperty(name="Calculate tangents",
	#						description="Calculate tangent space vectors",
	#						default=False)

	
	@classmethod
	def poll(cls, context):
		return context.active_object.type in ['MESH', 'EMPTY']

	def execute(self, context):
		start_time = time.time()
		print('\n_____START_____')
		props = self.properties
		filepath = self.filepath
		filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

		exported = do_export(context, props, filepath)
		
		if exported:
			print('finished export in %s seconds' %((time.time() - start_time)))
			print(filepath)
			
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager

		if True:
			# File selector
			wm.fileselect_add(self) # will run self.execute()
			return {'RUNNING_MODAL'}
		elif True:
			# search the enum
			wm.invoke_search_popup(self)
			return {'RUNNING_MODAL'}
		elif False:
			# Redo popup
			return wm.invoke_props_popup(self, event) #
		elif False:
			return self.execute(context)

###### EXPORT OPERATOR #######
class Export_anic(bpy.types.Operator, ExportHelper):
	'''Exports the active Object Animation as an NAF File.'''
	bl_idname = "export_anim.naf"
	bl_label = "Export NAF File (.naf)"

	filename_ext = ".naf"
	
	animation_startFrame : bpy.props.IntProperty(name="Start frame", default=0)
	animation_endFrame : bpy.props.IntProperty(name="End frame", default = 20)

	@classmethod
	def poll(cls, context):
		return context.active_object.type in ['MESH', 'EMPTY']

	def execute(self, context):
		start_time = time.time()
		print('\n_____START_____')
		props = self.properties
		filepath = self.filepath
		filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

		exported = do_export_anim(context, props, filepath)
		
		if exported:
			print('finished export in %s seconds' %((time.time() - start_time)))
			print(filepath)
			
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager

		if True:
			# File selector
			wm.fileselect_add(self) # will run self.execute()
			return {'RUNNING_MODAL'}
		elif True:
			# search the enum
			wm.invoke_search_popup(self)
			return {'RUNNING_MODAL'}
		elif False:
			# Redo popup
			return wm.invoke_props_popup(self, event) #
		elif False:
			return self.execute(context)

### REGISTER ###

def menu_func_mesh(self, context):
	self.layout.operator(Export_objc.bl_idname, text="NMF File (.nmf)")

def menu_func_anim(self, context):
	self.layout.operator(Export_anic.bl_idname, text="NAF File (.naf)")
	
def register():
	Export_objc
	Export_anic

	bpy.utils.register_class(Export_objc)
	bpy.utils.register_class(Export_anic)

	
	bpy.types.TOPBAR_MT_file_export.append(menu_func_mesh)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_anim)

def unregister():
	bpy.utils.unregister_class(Export_objc)
	bpy.utils.unregister_class(Export_anic)

	bpy.types.TOPBAR_MT_file_export.remove(menu_func_mesh)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_anim)

if __name__ == "__main__":
	register()
