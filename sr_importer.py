bl_info = {
    "name": "3Division Importer forked by Av1ra",
    "author": "Jan Kerkes",
    "version": (2, 1),
    "blender": (4, 4, 3),
    "location": "File > Import",
    "description": "Import Model from 3Division NMF Mesh file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}

import bpy
from bpy.props import EnumProperty
from bpy_extras.io_utils import ImportHelper
import time
import mathutils, math, struct
import os
from os import remove
import shutil
import bmesh

from itertools import chain

from datetime import datetime
from datetime import timedelta

def writeString(file, string):
    file.write(bytes(string, 'UTF-8'))


def do_import(context, props, filepath, is_mods_format):
    # open files for writing
    debugFile = open(filepath + "_debug", "wt")  # Single debug file

    if is_mods_format:
        debugFile.write("Attempting import as Mods NMF...\n")
        expectedHeader = bytearray(b'fromObj\x00')
    else:
        debugFile.write("Attempting import as Original NMF...\n")
        expectedHeader = bytearray(b'B3DMH\x0010')

    # construct rotation matrix -90* around X axis
    mat_x90 = mathutils.Matrix.Rotation(-math.pi / 2, 4, 'X')
    # construct inverse transform to above
    mat_x90inv = mat_x90.copy()
    mat_x90inv.invert()

    # get list of selected objects from scene
    current_scene = context.scene

    # main lists that are output of scene selection data extraction
    materials = []
    materialsBlender = []
    models = []
    helpers = []

    # open files for reading
    file = open(filepath, "rb")

    debugFile.write("File opened\n")

    header = bytearray(file.read(8))

    debugFile.write("File header: " + str(header) + "\n")
    debugFile.write("Expected header: " + str(expectedHeader) + "\n")

    if (len(header) == len(expectedHeader)) and (all(x == y for x, y in zip(expectedHeader, header))):
        debugFile.write("File is a NMF File, continuing\n")
    else:
        debugFile.write("File is NOT a NMF file!!!\n")
        debugFile.flush()
        debugFile.close()
        file.flush()
        file.close()
        return False

    # read num materials
    numMaterials, = struct.unpack("<L", file.read(4))
    debugFile.write('numMaterials {:d}\n'.format(numMaterials))

    # read num nodes
    numNodes, = struct.unpack("<L", file.read(4))
    debugFile.write('numNodes {:d}\n'.format(numNodes))

    # read file size
    sizeTotal, = struct.unpack("<L", file.read(4))
    debugFile.write('sizeTotal {:d}\n'.format(sizeTotal))

    # read material names
    for materialIndex in range(numMaterials):
        try:
            materialName = file.read(64).decode('utf-8', errors='ignore').rstrip('\0')
        except UnicodeDecodeError:
            materialName = "Material_" + str(materialIndex)  # Default name

        materials.append(materialName);

        debugFile.write("Material Name: " + materialName + "\n")

        material = None

        for mat in bpy.data.materials:
            if mat.name == materialName:
                material = mat;

        if material == None:
            material = bpy.data.materials.new(name=materialName)

        materialsBlender.append(material)

    debugFile.write("Starting to read nodes\n")

    for node in range(numNodes):
        debugFile.write("Reading node " + str(node) + "\n")

        # read node type
        nodeType, = struct.unpack("<L", file.read(4))

        debugFile.write('nodeType {:d}\n'.format(nodeType))

        # parse as bone record
        if nodeType == 1:
            debugFile.write('reading bone data\n')

            debugFile.write('reading bone at position {:d}\n'.format(file.tell()))

            # read bone size
            boneSize, = struct.unpack("<L", file.read(4))

            # read bone name
            boneName = file.read(64).decode('UTF-8').rstrip('\0')

            debugFile.write(boneName);
            debugFile.write('\n')

            # read parent ID
            boneParentId, = struct.unpack("<h", file.read(2))

            # read num childs
            boneNumChilds, = struct.unpack("<h", file.read(2))

            boneMatrix = mathutils.Matrix()
            # world
            boneMatrix[0][0], boneMatrix[1][0], boneMatrix[2][0], boneMatrix[3][0] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][1], boneMatrix[1][1], boneMatrix[2][1], boneMatrix[3][1] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][2], boneMatrix[1][2], boneMatrix[2][2], boneMatrix[3][2] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][3], boneMatrix[1][3], boneMatrix[2][3], boneMatrix[3][3] = struct.unpack("<ffff",
                                                                                                    file.read(16))

            # local
            boneMatrix[0][0], boneMatrix[1][0], boneMatrix[2][0], boneMatrix[3][0] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][1], boneMatrix[1][1], boneMatrix[2][1], boneMatrix[3][1] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][2], boneMatrix[1][2], boneMatrix[2][2], boneMatrix[3][2] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][3], boneMatrix[1][3], boneMatrix[2][3], boneMatrix[3][3] = struct.unpack("<ffff",
                                                                                                    file.read(16))

            # file.write(struct.pack("<ffff", bone.worldMatrix[0][1], bone.worldMatrix[1][1], bone.worldMatrix[2][1], bone.worldMatrix[3][1]))

            # AABB
            boneAABBmin = mathutils.Vector((0.0, 0.0, 0.0))
            boneAABBmax = mathutils.Vector((0.0, 0.0, 0.0))

            boneAABBmin[0], boneAABBmin[1], boneAABBmin[2] = struct.unpack("<fff", file.read(12))
            boneAABBmax[0], boneAABBmax[1], boneAABBmax[2] = struct.unpack("<fff", file.read(12))

            # write transform - offset one
            boneMatrix[0][0], boneMatrix[1][0], boneMatrix[2][0], boneMatrix[3][0] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][1], boneMatrix[1][1], boneMatrix[2][1], boneMatrix[3][1] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][2], boneMatrix[1][2], boneMatrix[2][2], boneMatrix[3][2] = struct.unpack("<ffff",
                                                                                                    file.read(16))
            boneMatrix[0][3], boneMatrix[1][3], boneMatrix[2][3], boneMatrix[3][3] = struct.unpack("<ffff",
                                                                                                    file.read(16))

        # parse as helper record
        elif nodeType == 2:
            debugFile.write('reading helper data\n')

            debugFile.write('reading helper at position {:d}\n'.format(file.tell()))

            # read helper size
            helperSize, = struct.unpack("<L", file.read(4))

            # read helper name
            helperName = file.read(64).decode('UTF-8').rstrip('\0')

            debugFile.write(helperName);
            debugFile.write('\n')

            # read parent ID
            helperParentId, = struct.unpack("<h", file.read(2))

            # read num childs
            helperNumChilds, = struct.unpack("<h", file.read(2))

            helperMatrixWorld = mathutils.Matrix()

            # world
            helperMatrixWorld[0][0], helperMatrixWorld[1][0], helperMatrixWorld[2][0], helperMatrixWorld[3][0] = struct.unpack("<ffff",
                                                                                                                                    file.read(
                                                                                                                                        16))
            helperMatrixWorld[0][1], helperMatrixWorld[1][1], helperMatrixWorld[2][1], helperMatrixWorld[3][1] = struct.unpack("<ffff",
                                                                                                                                    file.read(
                                                                                                                                        16))
            helperMatrixWorld[0][2], helperMatrixWorld[1][2], helperMatrixWorld[2][2], helperMatrixWorld[3][2] = struct.unpack("<ffff",
                                                                                                                                    file.read(
                                                                                                                                        16))
            helperMatrixWorld[0][3], helperMatrixWorld[1][3], helperMatrixWorld[2][3], helperMatrixWorld[3][3] = struct.unpack("<ffff",
                                                                                                                                    file.read(
                                                                                                                                        16))

            debugFile.write('Helper matrix world')
            debugFile.write(str(helperMatrixWorld))

            helperMatrix = mathutils.Matrix()

            # local
            helperMatrix[0][0], helperMatrix[1][0], helperMatrix[2][0], helperMatrix[3][0] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))
            helperMatrix[0][1], helperMatrix[1][1], helperMatrix[2][1], helperMatrix[3][1] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))
            helperMatrix[0][2], helperMatrix[1][2], helperMatrix[2][2], helperMatrix[3][2] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))
            helperMatrix[0][3], helperMatrix[1][3], helperMatrix[2][3], helperMatrix[3][3] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))

            debugFile.write('Helper matrix local')
            debugFile.write(str(helperMatrix))

            # AABB
            helperAABBmin = mathutils.Vector((0.0, 0.0, 0.0))
            helperAABBmax = mathutils.Vector((0.0, 0.0, 0.0))

            helperAABBmin[0], helperAABBmin[1], helperAABBmin[2] = struct.unpack("<fff", file.read(12))
            helperAABBmax[0], helperAABBmax[1], helperAABBmax[2] = struct.unpack("<fff", file.read(12))

            helperMatrix[0][0], helperMatrix[1][0], helperMatrix[2][0], helperMatrix[3][0] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))
            helperMatrix[0][1], helperMatrix[1][1], helperMatrix[2][1], helperMatrix[3][1] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))
            helperMatrix[0][2], helperMatrix[1][2], helperMatrix[2][2], helperMatrix[3][2] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))
            helperMatrix[0][3], helperMatrix[1][3], helperMatrix[2][3], helperMatrix[3][3] = struct.unpack("<ffff",
                                                                                                                file.read(
                                                                                                                    16))

            debugFile.write('Helper matrix ???')
            debugFile.write(str(helperMatrix))

            object = bpy.data.objects.new(helperName, None)
            object.empty_display_type = 'CUBE'
            object.empty_display_size = 0.5
            object.matrix_world[:] = mat_x90inv @ helperMatrixWorld

            col = bpy.data.collections.get("Collection")
            col.objects.link(object)

        # parse as model record
        elif nodeType == 0:
            debugFile.write('reading model data\n')

            debugFile.write('reading model at position {:d}\n'.format(file.tell()))

            # read helper size
            modelSize, = struct.unpack("<L", file.read(4))

            debugFile.write('modelSize {:d}\n'.format(modelSize))

            # read helper name
            try:
                modelName = file.read(64).decode('utf-8').rstrip('\0')
            except UnicodeDecodeError:
                modelName = "Model_" + str(node)  # Default name

            debugFile.write(modelName);
            debugFile.write('\n')

            # read parent ID
            modelParentId, = struct.unpack("<h", file.read(2))

            # read num childs
            modelNumChilds, = struct.unpack("<h", file.read(2))

            finalMatrixToApply = mathutils.Matrix()
            # mat_x90, mat_x90inv,
            # finalMatrixToApply = mat_x90 @ worldMatrix
            # mesh.transform(mat_x90inv)

            modelMatrix = mathutils.Matrix()

            # world
            modelMatrix[0][0], modelMatrix[1][0], modelMatrix[2][0], modelMatrix[3][0] = struct.unpack("<ffff",
                                                                                                        file.read(16))
            modelMatrix[0][1], modelMatrix[1][1], modelMatrix[2][1], modelMatrix[3][1] = struct.unpack("<ffff",
                                                                                                        file.read(16))
            modelMatrix[0][2], modelMatrix[1][2], modelMatrix[2][2], modelMatrix[3][2] = struct.unpack("<ffff",
                                                                                                        file.read(16))
            modelMatrix[0][3], modelMatrix[1][3], modelMatrix[2][3], modelMatrix[3][3] = struct.unpack("<ffff",
                                                                                                        file.read(16))

            # local
            modelMatrix[0][0], modelMatrix[1][0], modelMatrix[2][0], modelMatrix[3][0] = struct.unpack("<ffff",
                                                                                                        file.read(16))
            modelMatrix[0][1], modelMatrix[1][1], modelMatrix[2][1], modelMatrix[3][1] = struct.unpack("<ffff",
                                                                                                        file.read(16))
            modelMatrix[0][2], modelMatrix[1][2], modelMatrix[2][2], modelMatrix[3][2] = struct.unpack("<ffff",
                                                                                                        file.read(16))
            modelMatrix[0][3], modelMatrix[1][3], modelMatrix[2][3], modelMatrix[3][3] = struct.unpack("<ffff",
                                                                                                        file.read(16))

            # AABB
            modelAABBmin = mathutils.Vector((0.0, 0.0, 0.0))
            modelAABBmax = mathutils.Vector((0.0, 0.0, 0.0))

            modelAABBmin[0], modelAABBmin[1], modelAABBmin[2] = struct.unpack("<fff", file.read(12))
            modelAABBmax[0], modelAABBmax[1], modelAABBmax[2] = struct.unpack("<fff", file.read(12))

            # read num lods
            modelNumLODs, = struct.unpack("<L", file.read(4))
            debugFile.write('modelNumLODs {:d}\n'.format(modelNumLODs))

            for lod in range(modelNumLODs):
                # read size of LOD
                modelLODSize, = struct.unpack("<L", file.read(4))

                # read num vertices
                numVertices, = struct.unpack("<L", file.read(4))

                debugFile.write('numVertices {:d}\n'.format(numVertices))

                # read num indices
                numIndices, = struct.unpack("<L", file.read(4))

                debugFile.write('numIndices {:d}\n'.format(numIndices))

                # read num subsets
                numSubsets, = struct.unpack("<L", file.read(4))

                debugFile.write('numSubsets {:d}\n'.format(numSubsets))

                # read num morph targets
                numMorphTargets, = struct.unpack("<L", file.read(4))

                # read vertex attributes
                vertexAttributes, = struct.unpack("<L", file.read(4))

                debugFile.write('vertexAttributes {:d}\n'.format(vertexAttributes))

                # read vertex attributes
                morphMask, = struct.unpack("<L", file.read(4))

                # read vertex indices
                vertexListIndices = [0] * numIndices
                for i in range(numIndices):
                    vertexListIndices[i], = struct.unpack("<H", file.read(2))

                faces = []

                numFaces = numIndices // 3

                for i in range(numFaces):
                    face = [vertexListIndices[i * 3 + 0], vertexListIndices[i * 3 + 1],
                            vertexListIndices[i * 3 + 2]]
                    faces.append(face)

                # debugFile.write( str(vertexListIndices))

                # read write positions
                vertexPositionsList = []
                for i in range(numVertices):
                    position = mathutils.Vector((0.0, 0.0, 0.0))
                    position[0], position[1], position[2] = struct.unpack("<fff", file.read(12))
                    vertexPositionsList.append(position)

                # debugFile.write( str(vertexPositionsList))

                # read normals:
                vertexNormalsList = []
                if vertexAttributes & (1 << 3):
                    for i in range(numVertices):
                        normal = mathutils.Vector((0.0, 0.0, 0.0))
                        normal[0], normal[1], normal[2] = struct.unpack("<fff", file.read(12))

                        normal.normalize()

                        # normal[0] = 0.0
                        # normal[1] = 1.0
                        # normal[2] = 0.0
                        vertexNormalsList.append(normal)

                # debugFile.write( str(vertexNormalsList))

                # read tangents:
                vertexTangentsList = []
                if vertexAttributes & (1 << 4):
                    for i in range(numVertices):
                        tangent = mathutils.Vector((0.0, 0.0, 0.0))
                        tangent[0], tangent[1], tangent[2] = struct.unpack("<fff", file.read(12))
                        tangent.normalize()
                        vertexTangentsList.append(tangent)

                # read bitangents:
                vertexBiTangentsList = []
                if vertexAttributes & (1 << 5):
                    for i in range(numVertices):
                        bitangent = mathutils.Vector((0.0, 0.0, 0.0))
                        bitangent[0], bitangent[1], bitangent[2] = struct.unpack("<fff", file.read(12))
                        bitangent.normalize()
                        vertexBiTangentsList.append(bitangent)

                # read uvs:
                vertexUVList = []
                if vertexAttributes & (1 << 8):
                    for i in range(numVertices):
                        uv = mathutils.Vector((0.0, 0.0))
                        uv[0], uv[1] = struct.unpack("<ff", file.read(8))
                        vertexUVList.append(uv)

                # debugFile.write( str(vertexUVList))

                # skip bone influences:
                if vertexAttributes & (1 << 16):
                    file.seek(12 * numVertices, 1)

                # skip face planes
                if vertexAttributes & (1 << 18):
                    file.seek(10 * 4 * numIndices // 3, 1)

                debugFile.write('reading subset at position {:d}\n'.format(file.tell()))

                # subsets
                subsetArrayStartIndices = []
                subsetArrayNumIndices = []
                subsetArrayMaterials = []

                for i in range(numSubsets):
                    debugFile.write('reading subset {:d}\n'.format(i))

                    subsetStart, = struct.unpack("<L", file.read(4))
                    subsetArrayStartIndices.append(subsetStart)

                    debugFile.write('subsetStart {:d}\n'.format(subsetStart))

                    subsetNumIndices, = struct.unpack("<L", file.read(4))
                    subsetArrayNumIndices.append(subsetNumIndices)

                    debugFile.write('subsetNumIndices {:d}\n'.format(subsetNumIndices))

                    subsetMaterialIndex, = struct.unpack("<H", file.read(2))
                    subsetArrayMaterials.append(subsetMaterialIndex)

                    debugFile.write('subsetMaterialIndex {:d}\n'.format(subsetMaterialIndex))

                    subsetNumBones, = struct.unpack("<H", file.read(2))

                    debugFile.write('subsetNumBones {:d}\n'.format(subsetNumBones))

                    file.seek(2 * subsetNumBones, 1)

                # now construct blender object from this LOD
                mesh = bpy.data.meshes.new(modelName)
                object = bpy.data.objects.new(modelName, mesh)

                col = bpy.data.collections.get("Collection")
                if col is None:
                    col = bpy.data.collections.new("Collection")
                    bpy.context.scene.collection.children.link(col)  # Link to the main scene collection

                col.objects.link(object);

                bpy.context.view_layer.objects.active = object

                edges = []

                # ------------- way N1 ---------------------------
                mesh.from_pydata(vertexPositionsList, edges, faces)

                uv_layer = mesh.uv_layers.new()

                # mesh.use_auto_smooth = True
                mesh.shade_smooth()
                # mesh.auto_smooth_angle = math.radians(30)

                # Проверяем, существует ли UV-развертка
                if mesh.uv_layers:
                    uv_layer = mesh.uv_layers[0]  # Получаем первую UV-развертку
                else:
                    uv_layer = mesh.uv_layers.new(name="UVMap")  # Создаем новую, если не существует

                # Присваиваем UV-координаты каждой вершине
                for poly in mesh.polygons:
                    for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        vertex_index = mesh.loops[loop_index].vertex_index
                        uv_layer.data[loop_index].uv[0] = vertexUVList[vertex_index].x
                        uv_layer.data[loop_index].uv[1] = 1.0 - vertexUVList[vertex_index].y

                mesh.normals_split_custom_set_from_vertices(vertexNormalsList);

                # subsetArrayStartIndices = []
                # subsetArrayNumIndices = []
                # subsetArrayMaterials = []

                materialIndexesForThisModel = []

                # create list of indexes to materials used by this LOD/MESH
                for i in range(numSubsets):
                    if subsetArrayMaterials[i] not in materialIndexesForThisModel:
                        materialIndexesForThisModel.append(subsetArrayMaterials[i])

                # assign the materials to blender object
                for matIndex in materialIndexesForThisModel:
                    object.data.materials.append(materialsBlender[matIndex]);

                polygonIndex = 0
                for poly in mesh.polygons:
                    for subsetStartIndex, subsetNumIndices, subsetArrayMaterialIndex in zip(
                            subsetArrayStartIndices, subsetArrayNumIndices, subsetArrayMaterials):
                        vertexIndexOfPolygon = polygonIndex * 3

                        # now we know which subset this polygon belongs to
                        if (vertexIndexOfPolygon >= subsetStartIndex) and (
                                vertexIndexOfPolygon < subsetStartIndex + subsetNumIndices):

                            # convert subsetArrayMaterialIndex to index within model
                            for i in range(len(materialIndexesForThisModel)):
                                if materialIndexesForThisModel[i] == subsetArrayMaterialIndex:
                                    poly.material_index = i
                                    break
                            break

                    polygonIndex = polygonIndex + 1

                # ------------------------------------------------

                mesh.transform(mat_x90inv)
                mesh.update(calc_edges=True, calc_edges_loose=True)
                # bpy.context.collection.objects.link(object)
                # bpy.context.collection.objects.active = object
                # object.select = True


    debugFile.flush()
    debugFile.close()

    file.flush()
    file.close()

    return True


###### IMPORT OPERATOR #######
class Import_objc(bpy.types.Operator, ImportHelper):
    '''Imports NMF File as Mesh'''
    bl_idname = "file.nmf"
    bl_label = "Import .nmf"

    filename_ext = ".nmf"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        start_time = time.time()
        print('\n_____START_____')
        props = self.properties
        filepath = self.filepath
        #filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        try:
            imported = do_import(context, props, filepath, False)  # is_mods_format=False for Original
            if imported:
                print('finished import in %s seconds' % ((time.time() - start_time)))
                print(filepath)
                return {'FINISHED'}
        except Exception as e:
            print(f"Error importing as Original NMF: {e}")

        print("Attempting to import NMF...")
        try:
            imported = do_import(context, props, filepath, True)  # is_mods_format=True for Mods
            if imported:
                print('finished import in %s seconds' % ((time.time() - start_time)))
                print(filepath)
                return {'FINISHED'}
        except Exception as e:
            print("Error importing NMF: {e}")

        # If both imports failed, report an error
        self.report({'ERROR'}, "Failed to import NMF file")
        return {'CANCELLED'}

    def invoke(self, context, event):
        wm = context.window_manager

        if True:
            # File selector
            wm.fileselect_add(self)  # will run self.execute()
            return {'RUNNING_MODAL'}
        elif True:
            # search the enum
            wm.invoke_search_popup(self)
            return {'RUNNING_MODAL'}
        elif False:
            # Redo popup
            return wm.invoke_props_popup(self, event)  #
        elif False:
            return self.execute(context)


### REGISTER ###

def menu_func_imp_mesh(self, context):
    self.layout.operator(Import_objc.bl_idname, text="NMF File (.nmf)")


def register():
    Import_objc

    bpy.utils.register_class(Import_objc)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_imp_mesh)


def unregister():
    bpy.utils.unregister_class(Import_objc)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_imp_mesh)


if __name__ == "__main__":
    register()