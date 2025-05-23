from os import environ
from re import findall, compile as re_compile
from pathlib import Path

try:
    import maya.cmds as cmds  # type: ignore
    import maya.mel as mel  # type: ignore
    import maya.OpenMaya as om  # type: ignore
    from maya.api.OpenMaya import MGlobal  # type: ignore

except ImportError as e:
    pass

from core import Check, Context
from pipe_utils import underline_string_diferences  # type: ignore

try:
    import maya_utils as mu  # type: ignore
    from maya_utils import (  # type: ignore
        delete_all_lights,
        delete_all_nodes_by_type,
        return_empty_namespaces,
        filter_out_referenced_nodes,
        return_unknown_nodes,
        return_intermediate_shapes,
        return_group_ids,
        return_non_inverted_normal_maps,
        return_geo_hash,
        return_meshes_with_animation,
        return_non_conected_anim_curves,
        return_unwelded_verts,
        return_empty_transforms,
        FindOverlappingFaces,
    )

    maya_error = MGlobal.displayError
    maya_warning = MGlobal.displayWarning
    maya_info = MGlobal.displayInfo
except Exception as e:
    print(e)

class CheckRepeatedNameNodes(Check):
    name = "Check repeated node names"
    info = "Checks whether there are 2 or more nodes\n" "sharing the same short name."

    def process(self, context: Context) -> None:
        status = True
        errors = []

        status = True
        all_dag_list_long = cmds.ls(type="transform", l=True)
        all_dag_list_short = [item.split("|")[-1] for item in all_dag_list_long]
        all_dag_set = set(all_dag_list_short)
        diff = []
        repeated_nodes = []
        errors_nodes = []
        errors = []

        if len(all_dag_list_short) != len(all_dag_set):
            for item in all_dag_list_short:
                if item in all_dag_set:
                    all_dag_set.remove(item)
                else:
                    diff.append(item)

        for item in set(diff):
            for node in all_dag_list_long:
                if item in node:
                    repeated_nodes.append(node)

        if len(repeated_nodes) != 0:
            status = False
            for item in repeated_nodes:
                errors_nodes.append([item.split("|")[-1], item])
            errors = [{"text": "Repeated node names", "list": errors_nodes}]

        return status, errors


class CheckPastedNodes(Check):
    name = "Checks pasted nodes"
    info = "Checks whether there is any pasted node.\n"

    def process(self, context: Context) -> None:
        status = True
        errors = []
        self.errors_nodes = []

        for node in cmds.ls(ap=True, l=True):
            if "pasted__" in node:
                self.errors_nodes.append([node.split("|")[-1], node])
                status = False

        if not status:
            errors = [{"text": "Pasted nodes", "list": self.errors_nodes}]

        return status, errors

    def fix_method(self):
        for node in cmds.ls(ap=True, l=True):
            if "pasted__" not in node:
                continue
            try:
                if cmds.objExists(node):
                    cmds.delete(node)
            except Exception as e:
                print("[ERROR] - Failed to remove the node {} ->".format(node))
                print(e)


class CheckUnknownNodes(Check):
    name = "Check unknown nodes"
    info = "Looks for unknown nodes\n" "and if so, fixing will remove them."

    def process(self, context: Context) -> None:
        self.unknown_nodes = list(return_unknown_nodes())
        if len(self.unknown_nodes) != 0:
            all_unknown_nodes = [[item, item] for item in self.unknown_nodes]
            errors = [{"text": "There are unknown nodes", "list": all_unknown_nodes}]
            status = False
        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self):
        for node in self.unknown_nodes:
            try:
                try:
                    if cmds.lockNode(node, query=True, lock=True)[0]:
                        cmds.lockNode(node, lock=False)
                except:
                    pass
                cmds.delete(node)
            except:
                pass


class CheckEmptyNamespaces(Check):
    name = "Check empty namespaces"
    info = "Looks for empty namespaces\n" "and if so, fixing will remove them."

    def process(self, context: Context) -> None:
        self.empty_namespaces = list(return_empty_namespaces())
        if len(self.empty_namespaces) != 0:
            all_empty_namespaces = [[item, item] for item in self.empty_namespaces]
            errors = [
                {"text": "There are empty namespaces", "list": all_empty_namespaces}
            ]
            status = False
        else:
            errors = []
            status = True
        return status, errors

    def fix_method(self):
        mu.remove_empty_namespaces()


class CheckNoNamespaces(Check):
    name = "Check no namespaces"
    info = "Looks for namespaces\n" "and if so, fixing will remove them."

    def process(self, context: Context) -> None:
        non_default_ns = [[item, item] for item in mu.return_non_default_namespaces()]
        if non_default_ns:
            errors = [
                {"text": "There are non default namespaces", "list": non_default_ns}
            ]
            status = False
        else:
            status = True
            errors = list()
        return status, errors

    def fix_method(self):
        mu.delete_all_namespaces()


class CheckIntermediateShapes(Check):
    name = "Check non connected intermediate shapes"
    info = (
        "Looks for non connected intermediate shapes\n"
        "and if so, fixing will remove them."
    )

    def process(self, context: Context) -> None:
        self.disconnected_shapes = list(return_intermediate_shapes())
        if len(self.disconnected_shapes) != 0:
            all_disconnected_shapes = [
                [item, item] for item in self.disconnected_shapes
            ]
            errors = [
                {
                    "text": "There are disconnected intermediate shapes",
                    "list": all_disconnected_shapes,
                }
            ]
            status = False

        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self):
        for shape in self.disconnected_shapes:
            cmds.delete(shape)


class CheckNotConnectedGroupID(Check):
    name = "Check non connected groups IDs"
    info = "Looks for non connected groups ids\n" "and if so, fixing will remove them."

    def process(self, context: Context) -> None:
        self.disconnected_group_id = list(return_group_ids())
        if len(self.disconnected_group_id) != 0:
            all_disconnected_group_id = [
                [item, item] for item in self.disconnected_group_id
            ]
            errors = [
                {
                    "text": "There are disconnected group ids",
                    "list": all_disconnected_group_id,
                }
            ]
            status = False

        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self):
        for group in self.disconnected_group_id:
            cmds.delete(group)


class CheckNotInvertedNormalMaps(Check):
    name = "Check non inverted normal maps"
    info = "Looks for arnold normal nodes\n" "and checks whether they are inverted."

    def process(self, context: Context) -> None:
        self.non_inverted_normals = list(return_non_inverted_normal_maps())
        if len(self.non_inverted_normals) != 0:
            all_non_inverted_normals = [
                [item, item] for item in self.non_inverted_normals
            ]
            errors = [
                {
                    "text": "There are inverted normal maps",
                    "list": all_non_inverted_normals,
                }
            ]
            status = False

        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self):
        for node in self.non_inverted_normals:
            cmds.setAttr("{}.invertY".format(node), 1)


class CheckStarLike(Check):
    """
    Starlike polygons are a type of nGons, where the angles
    between the edges meet certain criteria.
    This check is deprecated for now on in Grisu pipeline.
    """

    name = "Find starlike poligons"
    info = (
        "Looks at all the meshes and its topology\n"
        "and returns a list with starlike polys."
    )

    def process(self, context: Context) -> None:
        errors = []
        error_detect = []
        status = True

        selection_list = om.MSelectionList()
        dag_path = om.MDagPath()
        om.MGlobal.getActiveSelectionList(selection_list)
        selection_iterator = om.MItSelectionList(selection_list)
        selection_list.getDagPath(0, dag_path)

        while not selection_iterator.isDone():
            mesh = om.MDagPath()
            component = om.MObject()
            selection_iterator.getDagPath(mesh, component)
            poly_it = om.MItMeshPolygon(mesh, component)
            while not poly_it.isDone():
                if poly_it.isStarlike() == False:
                    polygon_index = poly_it.index()
                    component_name = f"{dag_path.fullPathName()}.f[{polygon_index}]"
                    error_detect.append([component_name, component_name])
                    status = False
                else:
                    pass
                poly_it.next()
            selection_iterator.next()

        if error_detect:
            errors.append({"text": "Starlike polygons detect", "list": error_detect})

        return status, errors


class CheckTopology(Check):
    name = "Check all the topology"
    info = "Looks at all the meshes and its topology\n" "and returns lists with errors."

    def process(self, context: Context) -> None:
        errors = []
        status = True

        cmds.select(cmds.ls(type="mesh", l=True), r=True)
        self.invalid_edges = cmds.polyInfo(ie=True) or []
        self.invalid_vertices = cmds.polyInfo(iv=True) or []
        self.lamina_faces = cmds.polyInfo(lf=True) or []
        self.non_manifold_edges = cmds.polyInfo(nme=True) or []
        self.non_manifold_uv_edges = cmds.polyInfo(nue=True) or []
        self.non_manifold_uvs = cmds.polyInfo(nuv=True) or []
        self.non_manifold_verteces = cmds.polyInfo(nmv=True) or []
        cmds.select(cl=True)
        self.ngon_faces = (
            mel.eval(
                'polyCleanupArgList 4 { "1","0","1","0","1","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };'
            )
            or []
        )
        self.faces_with_holes = (
            mel.eval(
                'polyCleanupArgList 4 { "1","0","1","0","0","0","1","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };'
            )
            or []
        )
        self.zero_length_edges = (
            mel.eval(
                'polyCleanupArgList 4 { "1","0","1","0","0","0","0","0","0","1e-05","1","1e-05","0","1e-05","0","-1","0","0" };'
            )
            or []
        )
        self.zero_area_polys = (
            mel.eval(
                'polyCleanupArgList 4 { "1","0","1","0","0","0","0","0","1","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };'
            )
            or []
        )
        self.zero_uv_polys = (
            mel.eval(
                'polyCleanupArgList 4 { "1","0","1","0","0","0","0","0","0","1e-06","0","1e-06","1","1e-06","0","-1","0","0" };'
            )
            or []
        )
        self.invalid_components = (
            mel.eval(
                'polyCleanupArgList 4 { "1","2","1","0","0","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","1" };'
            )
            or []
        )

        cmds.select(cl=True)

        if len(self.invalid_edges) != 0:
            all_invalid_edges = [[item, item] for item in self.invalid_edges]
            errors.append(
                {"text": "There are invalid edges", "list": all_invalid_edges}
            )
            status = False

        if len(self.invalid_vertices) != 0:
            all_invalid_vertices = [[item, item] for item in self.invalid_vertices]
            errors.append(
                {"text": "There are invalid verteces", "list": all_invalid_vertices}
            )
            status = False

        if len(self.lamina_faces) != 0:
            all_lamina_faces = [[item, item] for item in self.lamina_faces]
            errors.append({"text": "There are lamina faces", "list": all_lamina_faces})
            status = False

        if len(self.non_manifold_edges) != 0:
            all_non_manifold_edges = [[item, item] for item in self.non_manifold_edges]
            errors.append(
                {"text": "There are non-manifold edges", "list": all_non_manifold_edges}
            )
            status = False

        # if len(self.non_manifold_uv_edges) != 0:
        #     all_non_manifold_uv_edges = [
        #         [item, item] for item in self.non_manifold_uv_edges
        #     ]
        #     errors.append(
        #         {
        #             "text": "There are non manifold uv edges",
        #             "list": all_non_manifold_uv_edges,
        #         }
        #     )
        #     status = False

        # if len(self.non_manifold_uvs) != 0:
        #     all_non_manifold_uvs = [[item, item] for item in self.non_manifold_uvs]
        #     errors.append(
        #         {"text": "There are non manifold uvs", "list": all_non_manifold_uvs}
        #     )
        #     status = False

        if len(self.non_manifold_verteces) != 0:
            all_non_manifold_verteces = [
                [item, item] for item in self.non_manifold_verteces
            ]
            errors.append(
                {
                    "text": "There are non manifold verteces",
                    "list": all_non_manifold_verteces,
                }
            )
            status = False

        if len(self.ngon_faces) != 0:
            all_ngon_faces = [[item, item] for item in self.ngon_faces]
            errors.append({"text": "There are ngon faces", "list": all_ngon_faces})
            status = False

        if len(self.faces_with_holes) != 0:
            all_faces_with_holes = [[item, item] for item in self.faces_with_holes]
            errors.append(
                {"text": "There are faces with holes", "list": all_faces_with_holes}
            )
            status = False

        if len(self.zero_length_edges) != 0:
            all_zero_length_edges = [[item, item] for item in self.zero_length_edges]
            errors.append(
                {"text": "There are zero length edges", "list": all_zero_length_edges}
            )
            status = False

        if len(self.zero_area_polys) != 0:
            all_zero_area_polys = [[item, item] for item in self.zero_area_polys]
            errors.append(
                {"text": "There are zero area polygons", "list": all_zero_area_polys}
            )
            status = False

        # if len(self.zero_uv_polys) != 0:
        #     all_zero_uv_polys = [[item, item] for item in self.zero_uv_polys]
        #     errors.append(
        #         {"text": "There are zero uvs polygons", "list": all_zero_uv_polys}
        #     )
        #     status = False

        # if len(self.invalid_components) != 0:
        #     all_invalid_components = [[item, item] for item in self.invalid_components]
        #     errors.append(
        #         {"text": "There are zero uvs polygons", "list": all_invalid_components}
        #     )
        #     status = False

        # self_penetrating_UVs = []
        # for shape in cmds.ls(type="mesh", l=True):
        #     obj = cmds.listRelatives(p=True, f=True)
        #     convert_to_faces = cmds.ls(
        #         cmds.polyListComponentConversion(shape, tf=True), fl=True
        #     )
        #     overlapping = cmds.polyUVOverlap(convert_to_faces, oc=True)
        #     if overlapping is not None:
        #         for comp in overlapping:
        #             self_penetrating_UVs.append([comp, comp])

        # if len(self_penetrating_UVs) != 0:
        #     errors.append(
        #         {"text": "There are overlapping UVs", "list": self_penetrating_UVs}
        #     )
        #     status = False

        return status, errors

    def fix_method(self):
        mel.eval(
            'polyCleanupArgList 4 { "0","1","1","0","0","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","1","1","1" };'
        )


class CheckUVs(Check):
    name = "Check all the UVs"
    info = "Looks at all the meshes and its UVs\n" "and returns lists with errors."

    def process(self, context: Context) -> None:
        errors = []
        status = True

        cmds.select(cmds.ls(type="mesh", l=True), r=True)
        self.non_manifold_uv_edges = cmds.polyInfo(nue=True) or []
        self.non_manifold_uvs = cmds.polyInfo(nuv=True) or []
        cmds.select(cl=True)

        self.zero_uv_polys = (
            mel.eval(
                'polyCleanupArgList 4 { "1","0","1","0","0","0","0","0","0","1e-06","0","1e-06","1","1e-06","0","-1","0","0" };'
            )
            or []
        )

        cmds.select(cl=True)

        if len(self.non_manifold_uv_edges) != 0:
            all_non_manifold_uv_edges = [
                [item, item] for item in self.non_manifold_uv_edges
            ]
            errors.append(
                {
                    "text": "There are non manifold uv edges",
                    "list": all_non_manifold_uv_edges,
                }
            )
            status = False

        if len(self.non_manifold_uvs) != 0:
            all_non_manifold_uvs = [[item, item] for item in self.non_manifold_uvs]
            errors.append(
                {"text": "There are non manifold uvs", "list": all_non_manifold_uvs}
            )
            status = False

        if len(self.zero_uv_polys) != 0:
            all_zero_uv_polys = [[item, item] for item in self.zero_uv_polys]
            errors.append(
                {"text": "There are zero uvs polygons", "list": all_zero_uv_polys}
            )
            status = False

        self_penetrating_UVs = []
        for shape in cmds.ls(type="mesh", l=True):
            obj = cmds.listRelatives(p=True, f=True)
            convert_to_faces = cmds.ls(
                cmds.polyListComponentConversion(shape, tf=True), fl=True
            )
            overlapping = cmds.polyUVOverlap(convert_to_faces, oc=True)
            if overlapping is not None:
                for comp in overlapping:
                    self_penetrating_UVs.append([comp, comp])

        if len(self_penetrating_UVs) != 0:
            errors.append(
                {"text": "There are overlapping UVs", "list": self_penetrating_UVs}
            )
            status = False

        return status, errors


class CheckLights(Check):
    name = "Check light nodes"
    info = "Checks whether there is any light\n" "in the file."

    def process(self, context: Context) -> None:
        """
        Checks whether all the dependencies has the environemnt variable in them.

        status : Bool
        errors : List errors = {"text":Informacion del error,"list":error_objects}
        error_objects : Error list objects = [node error, object]
        return : {"status":status,"errors":errors}
        """
        status = True
        errors = []
        error_objects = []

        for item in cmds.ls(dag=True):
            if "lightData" in cmds.listAttr(item):
                error_objects.append(
                    [item, cmds.listRelatives(item, parent=True, fullPath=True)[0]]
                )
                status = False

        if status == False:
            errors.append({"text": "Lights in file", "list": error_objects})

        return status, errors

    def fix_method(self):
        delete_all_lights()


class CheckResidualAovs(Check):
    name = "Check residual AOVs"
    info = "Checks residual AOVs\n" "in the file."

    def process(self, context: Context) -> None:
        """
        Checks whether all the dependencies has the environemnt variable in them.

        status : Bool
        errors : List errors = {"text":Informacion del error,"list":error_objects}
        error_objects : Error list objects = [node error, object]
        return : {"status":status,"errors":errors}
        """
        try:
            import mtoa.core  # type: ignore
            import mtoa.aovs as aovs  # type: ignore
        except Exception as error:
            return False, [{"text": error, "list": []}]

        status = True
        errors = []
        error_objects = []

        mtoa.core.createOptions()

        list_aovs = aovs.AOVInterface().getAOVs()
        if list_aovs:
            for aov in list_aovs:
                error_objects.append([aov, aov])
                status = False

        if status == False:
            errors.append({"text": "Residual AOVs", "list": error_objects})

        return status, errors

    def fix_method(self):
        try:
            import mtoa.core  # type: ignore
            import mtoa.aovs as aovs  # type: ignore
        except Exception as error:
            return
        try:
            aovs.AOVInterface().removeAOVs(aovs.AOVInterface().getAOVs())  # type: ignore
        except Exception as error:
            maya_warning(error)


class CheckImagePlanes(Check):
    name = "Check ImagePlane nodes"
    info = "Checks whether there is any ImagePlane\n" "in the file."

    def process(self, context: Context) -> None:
        """
        Checks whether all the dependencies has the environemnt variable in them.

        status : Bool
        errors : List errors = {"text":Informacion del error,"list":error_objects}
        error_objects : Error list objects = [node error, object]
        return : {"status":status,"errors":errors}
        """
        status = True
        errors = []
        error_objects = []

        for node in cmds.ls(type="imagePlane"):
            error_objects.append(
                [node, cmds.listRelatives(node, parent=True, fullPath=True)[0]]
            )
            status = False
        if status == False:
            errors.append({"text": "ImagePlane in file", "list": error_objects})

        return status, errors

    def fix_method(self):
        delete_all_nodes_by_type("imagePlane")


class CheckSequenceManager(Check):
    name = "Check Sequencer manager nodes"
    info = "Checks whether there is any Sequencer manager nodes\n" "in the file."

    def process(self, context: Context) -> None:
        """
        Checks whether all the dependencies has the environemnt variable in them.

        status : Bool
        errors : List errors = {"text":Informacion del error,"list":error_objects}
        error_objects : Error list objects = [node error, object]
        return : {"status":status,"errors":errors}
        """

        ###########
        # VARIABLES#
        ###########

        status = True
        errors = []
        error_objects = []

        #######
        # CHECK#
        #######
        # file,reference, AlembicNode, aiImage, aiStandIn
        status = True
        for node in cmds.ls(type="shot"):
            error_objects.append([node, node])
            status = False

        for node in cmds.ls(type="sequencer"):
            error_objects.append([node, node])
            status = False

        for node in cmds.ls(type="trackInfoManager"):
            error_objects.append([node, node])
            status = False

        if status == False:
            errors.append(
                {"text": "Sequencer manager nodes in file", "list": error_objects}
            )

        return status, errors

    def fix_method(self):
        delete_all_nodes_by_type("shot", parent=False)
        delete_all_nodes_by_type("sequencer", parent=False)
        delete_all_nodes_by_type("trackInfoManager", parent=False)


class CheckScriptNodes(Check):
    name = "Check script node"
    info = "Check script node."

    def process(self, context: Context) -> None:
        status = True
        errors = []
        error_node = []

        for item in cmds.ls(type="script"):
            if not any(
                node in item
                for node in [
                    "sceneConfigurationScriptNode",
                    "uiConfigurationScriptNode",
                ]
            ):
                status = False
                error_node.append([item, item])

        if not status:
            errors.append({"text": "Unknown script nodes", "list": error_node})

        return status, errors

    def fix_method(self):
        for item in cmds.ls(type="script"):
            if not any(
                node in item
                for node in [
                    "sceneConfigurationScriptNode",
                    "uiConfigurationScriptNode",
                ]
            ):
                try:
                    cmds.delete(item)
                except Exception as e:
                    maya_warning(f"Failed to remove {item}.")
                    print(e)


class CheckOverlappingFaces(Check):
    name = "Check overlapping faces"
    info = "Looks for overlapping faces\n" "and if so, fixing will remove them."

    def __init__(self):
        super().__init__()
        self.list_of_hashes = []

    def checkChangesInHash(self):
        self.do_it = False
        for mesh in cmds.ls(type="mesh"):
            geo_hash = return_geo_hash(mesh, True, True, True)
            if geo_hash not in self.list_of_hashes:
                self.do_it = True
                self.list_of_hashes.append(geo_hash)

        if not self.do_it:
            return True

        else:
            return False

    def process(self, context: Context) -> None:
        errors = []
        overlap_finder = FindOverlappingFaces(
            vertical_precision=0.01, select_faces=False
        )
        self.overlapping_faces = []

        if overlap_finder.skipped:
            status = False
            maya_info("SKIPPED")
            errors = [{"text": "NO CHECKED", "list": ["NOT CHECKED"]}]
            return status, errors

        self.overlapping_faces = set(overlap_finder.faces_to_select)
        self.overlapping_nodes = set(overlap_finder.transforms_to_select)

        if len(self.overlapping_faces) != 0:
            all_overlapping_faces = [
                [item, item] for item in sorted(self.overlapping_faces)
            ]
            errors.append(
                {"text": "There are overlapping faces", "list": all_overlapping_faces}
            )
            status = False

        if len(self.overlapping_nodes) != 0:
            all_overlapping_nodes = [
                [item, item] for item in sorted(self.overlapping_nodes)
            ]
            errors.append(
                {"text": "There are overlapping nodes", "list": all_overlapping_nodes}
            )
        #     status = False
        else:
            status = True
        return status, errors

    def fix_method(self):
        for item in self.overlapping_faces:
            cmds.delete(item)


class CheckMeshesWhichHaveAnimation(Check):
    name = "Check meshes that have animation"
    info = (
        "Checks whether the meshes have any animation\n"
        "and if so, fixing will remove them."
    )

    def process(self, context: Context) -> None:
        self.anim_curves = list(return_meshes_with_animation())
        if len(self.anim_curves) != 0:
            all_anim_curves = [[item, item] for item in self.anim_curves]
            errors = [
                {"text": "There are animated geometries", "list": all_anim_curves}
            ]
            status = False

        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self):
        for item in list(return_meshes_with_animation()):
            cmds.delete(item)


class CheckUnusedAnimCurves(Check):
    name = "Check unused animation curves"
    info = (
        "This removes animation curves that are not connected\n"
        "and thus are useless.\n"
        "WARNING: If there are any proxies in the scene\n"
        "This may remove some existing animation connected to the anim. rig."
    )

    def process(self, context: Context) -> None:
        errors = []
        status = True
        self.errors_curves = list()
        self.useless_anim_curves = list(return_non_conected_anim_curves())
        if len(self.useless_anim_curves) != 0:
            all_anim_curves = [[item, item] for item in self.useless_anim_curves]
            errors = [
                {"text": "There are useless animation curves", "list": all_anim_curves}
            ]
            status = False
        # TODO:
        # if "episodes" not in self.MAYA_FILE_PATH:
        #     for node in cmds.ls(type = ["animCurveTL",
        #                                 "animCurveTA",
        #                                 "animCurveTT",
        #                                 "animCurveTU"],
        #                                 l = True):

        #         self.errors_curves.append([node.split("|")[-1], node])
        #         status = False
        #     errors = [{"text" : "There are animation curves but assets should not have them","list" : self.errors_curves}]

        return status, errors

    def fix_method(self):
        for item in self.useless_anim_curves:
            cmds.delete(item)

        for item in self.errors_curves:
            cmds.delete(item)


class CheckUnweldedVertex(Check):
    name = "Check unwelded verteces"
    info = "Checks whether there are unwelded verteces"

    def process(self, context: Context) -> None:
        self.unwelded_verts = list(return_unwelded_verts())
        if len(self.unwelded_verts) != 0:
            all_unwelded_verts = [[item, item] for item in self.unwelded_verts]
            errors = [
                {"text": "There are unwelded verteces", "list": all_unwelded_verts}
            ]
            status = False

        else:
            errors = []
            status = True

        return status, errors


class CheckEmptyTransforms(Check):
    name = "Check empty transforms"
    info = "Looks for empty transforms\n" "and if so, fixing will remove them."

    def process(self, context: Context) -> None:
        self.empty_transforms = list(return_empty_transforms())
        self.empty_transforms = [
            n
            for n in self.empty_transforms
            if n
            not in mu.return_asset_base_outliner_nodes()
            + mu.return_shot_base_outliner_nodes()
        ]
        if len(self.empty_transforms) != 0:
            all_empty_transforms = [[item, item] for item in self.empty_transforms]
            errors = [
                {
                    "text": "There are empty transform nodes",
                    "list": all_empty_transforms,
                }
            ]
            status = False
        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self):
        cmds.delete(self.empty_transforms)


class CheckResidualCams(Check):
    name = "Check residual cams"
    info = "Check residual cams."

    def process(self, context: Context) -> None:
        status = True
        errors = []
        list_errors = []
        list_show_errors = []

        for cam in cmds.ls(type="camera"):
            if cam not in ["frontShape", "perspShape", "sideShape", "topShape"]:
                list_errors.append([cam, cmds.listRelatives(cam, p=True, f=True)[0]])
                status = False
            else:
                if cmds.getAttr(
                    cmds.listRelatives(cam, p=True, f=True)[0] + ".visibility"
                ):
                    list_show_errors.append(
                        [cam, cmds.listRelatives(cam, p=True, f=True)[0]]
                    )
                    status = False

        if status == False:
            if list_errors:
                errors.append({"text": "Residual cameras", "list": list_errors})
            if list_show_errors:
                errors.append(
                    {"text": "Default cameras not hidden", "list": list_show_errors}
                )

        return status, errors

    def fix_method(self):
        for cam in cmds.ls(type="camera"):
            if cam in ["frontShape", "perspShape", "sideShape", "topShape"]:
                cmds.setAttr(
                    cmds.listRelatives(cam, p=True, f=True)[0] + ".visibility",
                    False,
                )


class CheckCorrectFPS(Check):
    name = "Check correct FPS"
    info = f"Checks the frames per second. For this project it should be {environ.get('GWAIO_FPS')}."

    def __init__(self):
        super().__init__()
        self.dict_types = {
            "game": "15",
            "film": "24",
            "pal": "25",
            "ntsc": "30",
            "show": "48",
            "palf": "50",
            "ntscf": "60",
        }
        self.correct_fps = environ.get("GWAIO_FPS")
        if self.correct_fps in self.dict_types.keys():
            pass
        elif self.correct_fps in self.dict_types.values():
            self.correct_fps = list(self.dict_types.keys())[
                list(self.dict_types.values()).index(self.correct_fps)
            ]
        else:
            self.correct_fps = f"{self.correct_fps}fps"

    def process(self, context: Context) -> None:
        status = True
        errors = []
        if not cmds.currentUnit(q=True, t=True) == self.correct_fps:
            status = False
        return status, errors

    def fix_method(self):
        cmds.currentUnit(t=self.correct_fps)


class CheckMayaFileNamingConvention(Check):
    name = "Check maya file naming convention"
    info = (
        "Checks whether the maya file has the correct naming convention.\nRules:\n"
        f"1.- The name must start with: '{environ.get('GWAIO_NAMING_HEAD')}'.\n"
        f"2.- The version must follow the pattern: '{environ.get('GWAIO_VERSION_REGEX')}'\n"
        "3.- Maya files should use Maya ASCII format, instead of Maya Binary."
    )

    def process(self, context: Context) -> None:
        status = True
        errors = []
        file_name = Path(cmds.file(q=True, l=True)[0]).name
        stem = Path(cmds.file(q=True, l=True)[0]).stem
        suffix = Path(cmds.file(q=True, l=True)[0]).suffix

        if not file_name.startswith(environ.get("GWAIO_NAMING_HEAD")):
            a, b = underline_string_diferences(
                environ.get("GWAIO_NAMING_HEAD"), file_name
            )
            errors.append(
                {
                    "text": f"The name must start with: '{environ.get('GWAIO_NAMING_HEAD')}'.",
                    "list": [[file_name, file_name], a.split("\n")[::-1]],
                }
            )
            status = False

        if not findall(environ.get("GWAIO_VERSION_REGEX"), file_name):
            status = False
            errors.append(
                {
                    "text": f"The version must be like: '{environ.get('GWAIO_VERSION_REGEX')}'",
                    "list": [[file_name, file_name]],
                }
            )
        if not file_name.endswith(".ma"):
            status = False
            errors.append(
                {
                    "text": "It should be Maya ASCII (.ma)",
                    "list": [
                        [file_name, file_name],
                        [" " * len(stem) + "^" * len(suffix), file_name],
                    ],
                }
            )

        # if not any(match(r, environ.get("GWAIO_NAMING_HEAD")) for r in GWAIO_VERSION_REGEX):
        #     errors.append({"text" : "Wrong maya file naming", "list" : [GWAIO_NAMING_HEAD,GWAIO_NAMING_HEAD]})
        # else:
        #     status = True

        return status, errors


class CheckNodeHistory(Check):
    name = "Check node history"
    info = "Checks if node has history."

    @staticmethod
    def return_nodes_with_history():
        return [n for n in cmds.ls(type=["mesh", "joint"], l=True) if mu.get_history(n)]

    def process(self, context: Context) -> None:
        """
        Checks whether all the nodes has the history clean.

        status : Bool
        errors : List errors = {"text":Informacion del error,"list":error_objects}
        error_objects : Error list objects = [node error, object]
        return : {"status":status,"errors":errors}
        """

        status = True
        errors = []
        error_objects = []

        for node in self.return_nodes_with_history():
            error_objects.append([node, node])
            status = False

        if status == False:
            errors.append(
                {"text": "Nodes with uncleaned history", "list": error_objects}
            )

        return status, errors

    def fix_method(self):
        cmds.select(self.return_nodes_with_history(), r=True)
        # mel.eval("BakeNonDefHistory;")
        mel.eval("DeleteHistory;")
        # print("Please clear history manually.")


class CheckOutliner(Check):
    name = "Base class for checking the outliner"
    entity_nodes = list()

    def __new__(cls):
        cls.info = (
            "Checks whether your outliner is tidy according to the project rules.\n"
            f"The base nodes must be: {', '.join(cls.entity_nodes)}"
        )
        return super().__new__(cls)

    def process(self, context: Context) -> None:
        status = True
        errors = []
        errors_hierarchy = []
        errors_main = []
        errors_name = []
        entity_nodes = self.entity_nodes  # mu.return_asset_base_outliner_nodes()

        basic_items = [
            "|side",
            "|left",
            "|back",
            "|bottom",
            "|front",
            "|persp",
            "|top",
            "|side|sideShape",
            "|left|leftShape",
            "|back|backShape",
            "|bottom|bottomShape",
            "|front|frontShape",
            "|persp|perspShape",
            "|top|topShape",
            "|",
        ] + entity_nodes

        # outliner_heads = cmds.ls("|*::*", l=True) + cmds.ls("|*", l=True)
        basic_items_parents = [
            node for n in basic_items for node in mu.return_parents_from_long_name(n)
        ]
        outliner_heads = cmds.ls(assemblies=True, l=True)
        compile_pattern_mesh = re_compile(r"[a-zA-Z0-9]+[0-9][0-9]_[L,R,U,D,M]_geo")
        compile_pattern_joint = re_compile(r"[a-zA-Z0-9]+[0-9][0-9]_[L,R,U,D,M]_jnt")

        # check whether there are bad assemblies
        for item in outliner_heads:
            if item not in basic_items and all(item not in n for n in entity_nodes):
                status = False
                errors_hierarchy.append([item.split("|")[-1], item])

        # check whether there are missing assemblies
        for node in entity_nodes:
            if not cmds.objExists(node):
                status = False
                errors_main.append([node.split("|")[-1], node])

        # check whether the are nodes that are missing a parent
        for node in cmds.ls(dag=True, l=True):
            if node not in basic_items + basic_items_parents and all(
                n not in node for n in entity_nodes
            ):
                status = False
                item = [node.split("|")[-1], node]
                if item not in errors_hierarchy:
                    errors_hierarchy.append([node.split("|")[-1], node])

        # check non-ascii characters in name
        errors_ascii = list()
        for item in cmds.ls(dag=True, l=True):
            try:
                item.encode()
            except:
                errors_ascii.append([item.split("|")[-1], item])

        errors.append(
            {"text": "Nodes not in hierachy (Manual fix)", "list": errors_hierarchy}
        )
        errors.append(
            {"text": "Missing main nodes (Automatic fix)", "list": errors_main}
        )
        # errors.append({"text": "Wrong naming of nodes", "list": errors_name})
        errors.append(
            {
                "text": "Non ascii characters were found (Manual fix)",
                "list": errors_ascii,
            }
        )

        # self.errors = errors

        return status, errors

    def fix_method(self):
        return list(mu.create_nodes_from_list(self.entity_nodes))


class CheckOutlinerShots(CheckOutliner):
    name = "Check the shots outliner"

    def __new__(cls):
        cls.entity_nodes = mu.return_shot_base_outliner_nodes()
        return super().__new__(cls)


class CheckOutlinerAssets(CheckOutliner):
    name = "Check the assets outliner"

    def __new__(cls):
        """
        NOTE: the reason why we create these here is because this module
        is imported by a module that does not support maya environment, to inspect
        the checks and generate an UI. By hiding the maya_utils in the new() we
        defer the execution of those lines until a new instance is created, and
        these instances are only created in a Maya Env.
        """
        cls.entity_nodes = mu.return_asset_base_outliner_nodes()
        return super().__new__(cls)


class CheckAssetsBaseGroupsTransforms(Check):
    name = "Check the base group's transforms."

    def __new__(cls):
        cls.entity_nodes = mu.return_asset_base_outliner_nodes()
        return super().__new__(cls)

    def process(self, context: Context) -> None:
        status = True
        errors = []
        error_reset = list()
        error_pivots = list()
        self.entity_nodes += list(
            set(
                node
                for n in self.entity_nodes
                for node in mu.return_parents_from_long_name(n)
            )
        )

        for node in self.entity_nodes:
            if not mu.is_transform_reset(node):
                error_reset.append([node, node])
                status = False
            if not mu.are_pivots_at_world_origin([node]):
                error_pivots.append([node, node])
                status = False

        if status == False:
            errors.append({"text": "The transforms are not reset", "list": error_reset})
            errors.append(
                {"text": "The pivots are not at scene origin", "list": error_pivots}
            )

        return status, errors

    def fix_method(self):
        unit_matrix = [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ]
        list(mu.create_nodes_from_list(self.entity_nodes))
        import traceback

        for node in self.entity_nodes:
            try:
                cmds.xform(node, m=unit_matrix)
                cmds.xform(node, ztp=True)
            except Exception as e:
                traceback.print_exc()
                maya_warning(str(e))


class CheckStartFrame(Check):
    name = "Check start frame"
    info = (
        "Check of the first frame of the shot.\n"
        f"The first frame of the shot must be frame {environ.get('GWAIO_START_FRAME')}."
    )

    def __init__(self):
        super().__init__()
        start_frame = environ.get("GWAIO_START_FRAME")

        self.correct_start_frame = float(start_frame) if start_frame else None

    def process(self, context: Context) -> None:
        status = True
        errors = []
        error_start_frame = []
        if self.correct_start_frame is None:
            pass
        elif (
            not cmds.playbackOptions(q=True, min=True) == self.correct_start_frame
            or not cmds.playbackOptions(q=True, ast=True) == self.correct_start_frame
        ):
            error_start_frame.append(
                [f"Shot doesn't start at frame {self.correct_start_frame}.", None]
            )
            status = False

        if status == False:
            errors.append(
                {"text": "Shot doesn't start at frame 101", "list": error_start_frame}
            )

        return status, errors

    def fix_method(self):
        cmds.playbackOptions(e=True, min=self.correct_start_frame)
        cmds.playbackOptions(e=True, ast=self.correct_start_frame)


class CheckEndFrame(Check):
    name = "Check end frame"
    info = (
        "Check of the last frame of the shot.\n"
        f"The last frame of the shot must be frame {environ.get('GWAIO_END_FRAME')}."
    )

    def __init__(self):
        super().__init__()
        end_frame = environ.get("GWAIO_END_FRAME")

        self.correct_end_frame = float(end_frame) if end_frame else None

    def process(self, context: Context) -> None:
        status = True
        errors = []
        error_end_frame = []
        if self.correct_end_frame is None:
            pass
        elif (
            not cmds.playbackOptions(q=True, max=True) == self.correct_end_frame
            or not cmds.playbackOptions(q=True, aet=True) == self.correct_end_frame
        ):
            error_end_frame.append(
                [f"Shot doesn't end at frame {self.correct_end_frame}.", None]
            )
            status = False

        if status == False:
            errors.append(
                {"text": "Shot doesn't end at frame 101", "list": error_end_frame}
            )

        return status, errors

    def fix_method(self):
        cmds.playbackOptions(e=True, max=self.correct_end_frame)
        cmds.playbackOptions(e=True, aet=self.correct_end_frame)


class CheckEmptyReferenceNodes(Check):
    name = "Check empty reference nodes"
    info = "Checks whether there are any empty reference nodes."

    def process(self, context: Context) -> None:
        error_rn = list(mu.return_empty_reference_nodes())
        if error_rn:
            return False, {"text": "There are empty reference nodes", "list": error_rn}
        return True, list()

    def fix_method(self):
        mu.remove_empty_reference_nodes()


class CheckEnviromentVariables(Check):
    name = "Check dependencies paths"
    info = "Checks whether any dependent file has the environment variable on them."

    def process(self, context: Context) -> None:
        errors = list()
        error_dependencies = list()
        status = True
        for node, dependency in mu.return_all_dependencies(
            resolve_udims=False, yield_nodes=True
        ):
            if not dependency.startswith("$GWAIO_LOCAL_ROOT"):
                status = False
                error_dependencies.append([node, node])

        if status == False:
            errors.append(
                {"text": "Nodes with uncleaned history", "list": error_dependencies}
            )

        return status, errors

    def fix_method(self):
        # mu.fix_missing_drive_references()
        mu.download_missing_references()
        mu.replace_all_roots_with_variables()


class CheckUnusedShadingNodes(Check):
    name = "Check unused shading nodes."
    info = "Checks whether there are any unused shading nodes."

    def process(self, context: Context) -> None:
        unused_nodes = mu.return_unused_shading_nodes() or []
        if unused_nodes:
            return False, [
                {"text": "Unused shading nodes", "list": [[n, n] for n in unused_nodes]}
            ]
        return True, list()

    def fix_method(self):
        for node in mu.return_unused_shading_nodes():
            try:
                cmds.delete(node)
            except:
                maya_warning(f"Failed to remove {node}.")
