#tools = ['Access Roads', 'Crane Path', 'Shared Path']
import os, arcpy, math
arcpy.overwriteOutput = True
##Tools below will add fields and set variables
#User Input
output_workspace = arcpy.GetParameterAsText(0)
tools = arcpy.GetParameterAsText(1).split(';')
ar_cl = arcpy.GetParameterAsText(2)
cp_cl = arcpy.GetParameterAsText(3)
sp_cl = arcpy.GetParameterAsText(4)
ar_w = arcpy.GetParameterAsText(5)
cp_w = arcpy.GetParameterAsText(6)
sp_w = arcpy.GetParameterAsText(7)
surface = arcpy.GetParameterAsText(8)
#Workspace
arcpy.env.workspace = output_workspace
edit = arcpy.da.Editor(output_workspace)
#Add Fields
def fields(input_fc, width):
    arcpy.management.AddField(input_fc, "long_slope", "DOUBLE", None, None, None, "long_slope", "NULLABLE", "NON_REQUIRED", '')
    arcpy.management.AddField(input_fc, "cross_slope", "DOUBLE", None, None, None, "cross_slope", "NULLABLE", "NON_REQUIRED", '')
    arcpy.management.AddField(input_fc, "width", "DOUBLE", None, None, None, "width", "NULLABLE", "NON_REQUIRED", '')
    arcpy.management.CalculateField(input_fc, "width", width, "PYTHON3", '', "TEXT")
    return None
##Edge Layers and Split
#Centerline Splitter
output_GPAL = os.path.join(output_workspace, "CL_Original_GeneratePointsAlongLines")
output_SAP = os.path.join(output_workspace, "CL_Original_SplitAtPoints")
output_F2F_L = os.path.join(output_workspace, "CL_SplitAtPointsF2F_Left")
output_F2F_R = os.path.join(output_workspace, "CL_SplitAtPointsF2F_Right")
#Even splitting. Without doing this, split lines makes several lines that are <0.1 feet long and screws everything up
def evenpoint(input_fc):
    arcpy.CreateFeatureclass_management(output_workspace, "CL_Original_GeneratePointsAlongLines", "POINT", input_fc)
    arcpy.DeleteFeatures_management(output_GPAL) #Delete previous values
    layer = arcpy.MakeFeatureLayer_management(input_fc, 'layer') #Make temp layer
    def div_solver():
        lengths = []
        split = []
        
        with arcpy.da.SearchCursor('layer', "SHAPE@LENGTH") as cursor:
            for row in cursor:
                if row[0] not in lengths:
                    lengths.append(row[0]) #Record lengths
        del cursor
        #arcpy.AddMessage('Lengths')
        for ele in lengths: #Normalize interval length to ~20
            divinterval = round(float(ele) / 20)
            dif20 = abs(20 - (ele / divinterval))
            if dif20 <= 1:
                remain = dif20 / divinterval
                remainadd = remain + 20
                split.append(remainadd / ele)   
            else:
                remain = dif20 / divinterval
                remainadd = remain + 19
                split.append(remainadd / ele)           
            
        return split
    split_percent = div_solver()
    arcpy.AddMessage('Split Percentage Complete')
    
    with arcpy.da.SearchCursor('layer', ["OID@"]) as cursor:
        for i, row in enumerate(cursor):   
            arcpy.SelectLayerByAttribute_management ('layer',"NEW_SELECTION", "OBJECTID = {}".format(row[0])) 
            arcpy.management.GeneratePointsAlongLines('layer', r"memory\blankGPAL", "PERCENTAGE", None, 100 * split_percent[i], "END_POINTS")
            arcpy.management.DeleteField(r"memory\blankGPAL", "ORIG_FID")
            arcpy.management.Append(r"memory\blankGPAL", output_GPAL)
    return None
##Split
#use indices for splitting percent and feature
def splitter (input_fc, width):
    evenpoint(input_fc)
    arcpy.AddMessage('CL Split Complete')
    arcpy.management.SplitLineAtPoint(input_fc, output_GPAL, output_SAP, "1 Feet")
    arcpy.management.AddField(output_SAP, "width", "DOUBLE", None, None, None, '', "NULLABLE", "NON_REQUIRED", '')
    arcpy.management.CalculateField(output_SAP, "width", int(width), "PYTHON3", '', "TEXT", "NO_ENFORCE_DOMAINS")
    arcpy.conversion.FeatureClassToFeatureClass(output_SAP, output_workspace, "CL_SplitAtPointsF2F_Left") 
    arcpy.conversion.FeatureClassToFeatureClass(output_SAP, output_workspace, "CL_SplitAtPointsF2F_Right") 
    return None
##CopyParallel
def copyparallel(plyP,sLength,side):
    part=plyP.getPart(0)
    Array=arcpy.Array()
    for ptX in part:
        dL=plyP.measureOnLine(ptX)
        ptX0=plyP.positionAlongLine (dL-0.01).firstPoint
        ptX1=plyP.positionAlongLine (dL+0.01).firstPoint
        dX=float(ptX1.X)-float(ptX0.X)
        dY=float(ptX1.Y)-float(ptX0.Y)
        lenV=math.hypot(dX,dY)
        sX=-dY*sLength/lenV;sY=dX*sLength/lenV
        if side == 'L':
            P=arcpy.Point(ptX.X+sX,ptX.Y+sY)
        elif side == 'R':
            P=arcpy.Point(ptX.X-sX, ptX.Y-sY)
        else:
            arcpy.AddMessage('Error: copy parallel, invalid side')
        Array.add(P)
    array = arcpy.Array([Array])
    section=arcpy.Polyline(array)
    return section
                                  
##Copy Left and Right
def updateLR():
    edit.startEditing(False,True)
    edit.startOperation()
    with arcpy.da.UpdateCursor(output_F2F_L,("Shape@","Width")) as cursor:
        for shp,w in cursor:
            LeftLine=copyparallel(shp,int(w)/2,'L')
            cursor.updateRow((LeftLine,w))
    del cursor
    with arcpy.da.UpdateCursor(output_F2F_R,("Shape@","Width")) as cursor:
        for shp,w in cursor:
            RightLine=copyparallel(shp,int(w)/2,'R')
            cursor.updateRow((RightLine,w))   
    del cursor
    edit.stopOperation()
    edit.stopEditing(True)
    #arcpy.AddMessage('Parallel layers updated')
    return None
##Find cross points, long points, then slopes for both
def long_points(input_fc, surface):
    arcpy.management.GeneratePointsAlongLines(input_fc, "CL_Long_Points", "PERCENTAGE", None, 100, "END_POINTS")
    arcpy.ddd.AddSurfaceInformation("CL_Long_Points", surface, "Z", "LINEAR", None, 1, 0, '')
    arcpy.conversion.FeatureClassToFeatureClass("CL_Long_Points", output_workspace, "CL_Long_Start", 'MOD("OBJECTID",2)=1')
    arcpy.conversion.FeatureClassToFeatureClass("CL_Long_Points", output_workspace, "CL_Long_End", 'MOD("OBJECTID",2)=0')
    arcpy.management.JoinField(input_fc, "OBJECTID", "CL_Long_Start", "OBJECTID", "Z")
    arcpy.management.JoinField(input_fc, "OBJECTID", "CL_Long_End", "OBJECTID", "Z")
    return None
def cross_points(surface):
    #Make parallel lines
    sapjoin = os.path.join(output_workspace, "CL_SplitAtPointsF2F_Join")
    cl_left = "CL_SplitAtPointsF2F_Left"
    cl_right = "CL_SplitAtPointsF2F_Right"
    parallel_fc = [cl_left, cl_right]
    for fc in parallel_fc:
        if fc == cl_left:
            arcpy.management.GeneratePointsAlongLines(cl_left, "CL_Cross_L", "PERCENTAGE", None, 50, None)
            arcpy.ddd.AddSurfaceInformation("CL_Cross_L", surface, "Z", "LINEAR", None, 1, 0, '')
            arcpy.management.JoinField(output_SAP, "OBJECTID", "CL_Cross_L", "OBJECTID", "Z")
        else:
            arcpy.management.GeneratePointsAlongLines(cl_right, "CL_Cross_R", "PERCENTAGE", None, 50, None)
            arcpy.ddd.AddSurfaceInformation("CL_Cross_R", surface, "Z", "LINEAR", None, 1, 0, '')
            arcpy.management.JoinField(output_SAP, "OBJECTID", "CL_Cross_R", "OBJECTID", "Z")
    return None
def slope_calc():
    arcpy.management.CalculateField(output_SAP, "long_slope", "abs(!Z!-!Z_1!)/!Shape_Length!", "PYTHON3", '', "TEXT")
    arcpy.management.CalculateField(output_SAP, "cross_slope", "abs(!Z_12!-!Z_12_13!)/!width!", "PYTHON3", '', "TEXT")
    return None
#Run through every tool
for ele in tools:
    arcpy.Delete_management("memory")
    if ele == "'Access Roads'":
        arcpy.AddMessage('---')
        arcpy.AddMessage(str(ele))
        
        fields(ar_cl, ar_w)
        arcpy.AddMessage('Fields Complete')
        
        splitter(ar_cl, ar_w)
        #arcpy.AddMessage('Parallel Created')
        
        updateLR()
        arcpy.AddMessage('Parallel Complete')
        
        long_points(output_SAP, surface)
        arcpy.AddMessage('Long points Complete')
        
        cross_points(surface)
        arcpy.AddMessage('Cross points Complete')
        
        slope_calc()
        arcpy.AddMessage('Slope Calculations Complete')
        arcpy.conversion.FeatureClassToFeatureClass(output_SAP, output_workspace, "Access_Road_Slopes")
        
        arcpy.AddMessage('*Access Roads Slopes Complete')
    elif ele == "'Crane Path'":
        arcpy.AddMessage('---')
        arcpy.AddMessage(str(ele))
        
        fields(cp_cl, cp_w)
        arcpy.AddMessage('Fields Complete')
        
        splitter(cp_cl, cp_w)
        #arcpy.AddMessage('Parallel Created')
        
        updateLR()
        arcpy.AddMessage('Parallel Complete')
        
        long_points(output_SAP, surface)
        arcpy.AddMessage('Long points Complete')
        
        cross_points(surface)
        arcpy.AddMessage('Cross points Complete')
        
        slope_calc()
        arcpy.AddMessage('Slope Calculations Complete')
        arcpy.conversion.FeatureClassToFeatureClass(output_SAP, output_workspace, "Crane_Path_Slopes")
        
        arcpy.AddMessage('*Crane Path Slopes Complete')
    elif ele == "'Shared Path'":
        arcpy.AddMessage('---')
        arcpy.AddMessage(str(ele))
        
        fields(sp_cl, sp_w)
        arcpy.AddMessage('Fields Complete')
        
        splitter(sp_cl, sp_w)
        #arcpy.AddMessage('Parallel Created')
        
        updateLR()
        arcpy.AddMessage('Parallel Complete')
        
        long_points(output_SAP, surface)
        arcpy.AddMessage('Long points Complete')
        
        cross_points(surface)
        arcpy.AddMessage('Cross points Complete')
        
        slope_calc()
        arcpy.AddMessage('Slope Calculations Complete')
        arcpy.conversion.FeatureClassToFeatureClass(output_SAP, output_workspace, "Shared_Path_Slopes")
        
        arcpy.AddMessage('*Shared Path Slopes Complete')
    else:
        arcpy.AddMessage('Error: invalid tools')
        
arcpy.AddMessage('---')
arcpy.AddMessage('Tool Complete')
