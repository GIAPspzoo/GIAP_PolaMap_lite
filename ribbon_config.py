from .utils import tr


RIBBON_DEFAULT = [
    {
        "tab_name": tr("Main Tools"),
        "tab_id": 'Main Tools',
        "sections": [
            {
                "label": tr("Project"),
                "btn_size": 30,
                "btns": [
                    ["mActionOpenProject", 0, 0],
                    ["mActionNewProject", 0, 1],
                    ["mActionSaveProject", 1, 0],
                    ["mActionSaveProjectAs", 1, 1]
                ]
            },

            {
                "label": tr("Navigation"),
                "btn_size": 30,
                "btns": [
                    ["mActionPan", 0, 0],
                    ["mActionZoomIn", 0, 1],
                    ["mActionZoomOut", 0, 2],
                    ["mActionZoomFullExtent", 0, 3],

                    ["mActionZoomToLayer", 1, 0],
                    ["mActionZoomToSelected", 1, 1],
                    ["mActionZoomLast", 1, 2],
                    ["mActionZoomNext", 1, 3]
                ]
            },

            {
                'label': tr('Attributes'),
                'btn_size': 30,
                'btns': [
                    ['mActionIdentify', 0, 0],
                    ['mActionSelectFeatures', 0, 1],
                    ['mActionDeselectAll', 1, 0],
                    ['mActionOpenTable', 1, 1],
                ],
            },

            {
                'label': tr('Measurement'),
                'btn_size': 30,
                'btns': [
                    ['mActionMeasure', 0, 0],
                    ['mActionMeasureArea', 0, 1],
                    ['mActionMeasureAngle', 1, 0],
                ],
            },

                {
                    'label': tr('Add Layer'),
                    'id': 'Add Layer',
                    'btn_size': 30,
                    'btns': [
                        ['mActionAddOgrLayer', 0, 0],
                        ['mActionAddWmsLayer', 0, 1],
                        ['mActionAddPgLayer', 0, 2],
                        ['mActionAddMeshLayer', 0, 3],
                        ['mActionAddWcsLayer', 0, 4],
                        ['mActionAddDelimitedText', 0, 5],
                        ['mActionAddMssqlLayer', 0, 6],
                        ['mActionAddDb2Layer', 1, 6],
                        ['mActionAddOracleLayer', 0, 7],
                        ['mActionAddRasterLayer', 1, 0],
                        ['mActionAddWfsLayer', 1, 1],
                        ['mActionAddSpatiaLiteLayer', 1, 2],
                        ['mActionAddVirtualLayer', 1, 3],
                        ['mActionAddAmsLayer', 1, 4],
                        ['mActionAddAfsLayer', 1, 5],
                    ],
                },

                {
                    'label': tr('Create Layer'),
                    'id': 'Create Layer',
                    'btn_size': 30,
                    'btns': [
                        ['mActionNewGeoPackageLayer', 0, 1],
                        ['mActionNewMemoryLayer', 0, 2],
                        ['mActionNewVectorLayer', 1, 1],
                        ['mActionNewSpatiaLiteLayer', 1, 2],
                        ['mActionNewVirtualLayer', 0, 3]
                    ],
                },

            {
                'label': tr('Prints'),
                'id': 'Prints',
                'btn_size': 30,
                'btns': [
                    ['mActionNewPrintLayout', 0, 0],
                    ['giapMyPrints', 0, 1],
                    ['mActionShowLayoutManager', 1, 0],
                ]
            },

        ]
    },

    {
        "tab_name": tr("Advanced Tools"),
        "tab_id": "Advanced Tools",
        "sections": [
            {
                'label': tr('Advanced attributes'),
                'btn_size': 30,
                'btns': [
                    ['mActionIdentify', 0, 0],
                    ['mActionSelectFeatures', 0, 1],
                    ['mActionSelectPolygon', 0, 2],
                    ['mActionSelectByExpression', 0, 3],
                    ['mActionInvertSelection', 0, 4],
                    ['mActionDeselectAll', 0, 5],

                    ['mActionOpenTable', 1, 0],
                    ['mActionStatisticalSummary', 1, 1],
                    ['mActionOpenFieldCalc', 1, 2],
                    ['mActionMapTips', 1, 3],
                    ['mActionNewBookmark', 1, 4],
                    ['mActionShowBookmarks', 1, 5],
                ],
            },

            {
                'label': tr('Labels'),
                'btn_size': 30,
                'btns': [
                    ['mActionLabeling', 0, 0],
                    ['mActionChangeLabelProperties', 0, 1],
                    ['mActionPinLabels', 0, 2],
                    ['mActionShowPinnedLabels', 0, 3],
                    ['mActionShowHideLabels', 0, 4],
                    ['mActionMoveLabel', 1, 0],
                    ['mActionRotateLabel', 1, 1],
                    ['mActionDiagramProperties', 1, 2],
                    ['mActionShowUnplacedLabels', 1, 3],
                ]
            },

            {
                'label': tr('Vector'),
                'btn_size': 30,
                'btns': [
                    ['mActionToggleEditing', 0, 0],
                    ['mActionSaveLayerEdits', 0, 1],
                    ['mActionVertexTool', 0, 2],
                    ['mActionUndo', 0, 3],
                    ['mActionRedo', 0, 4],

                    ['mActionAddFeature', 1, 0],
                    ['mActionMoveFeature', 1, 1],
                    ['mActionDeleteSelected', 1, 2],
                    ['mActionCutFeatures', 1, 3],
                    ['mActionCopyFeatures', 1, 4],
                    ['mActionPasteFeatures', 1, 5],
                ],
            },

            {
                'label': tr('Digitizing'),
                'btn_size': 30,
                'btns': [
                    ['EnableSnappingAction', 0, 0],
                    ['EnableTracingAction', 0, 1],
                    ['mActionRotateFeature', 0, 2],
                    ['mActionSimplifyFeature', 0, 3],
                    ['mActionAddRing', 0, 4],
                    ['mActionAddPart', 0, 5],
                    ['mActionFillRing', 0, 6],
                    ['mActionOffsetCurve', 0, 7],
                    ['mActionCircularStringCurvePoint', 0, 8],

                    ['mActionDeleteRing', 1, 0],
                    ['mActionDeletePart', 1, 1],
                    ['mActionReshapeFeatures', 1, 2],
                    ['mActionSplitParts', 1, 3],
                    ['mActionSplitFeatures', 1, 4],
                    ['mActionMergeFeatureAttributes', 1, 5],
                    ['mActionMergeFeatures', 1, 6],
                    ['mActionReverseLine', 1, 7],
                    ['mActionTrimExtendFeature', 1, 8],
                ]
            },
        ]
    },

    {
        "tab_name": tr("Vector"),
        "tab_id": "Vector",
        "sections": [
            {
                'label': tr('Geoprocessing Tools'),
                'id': 'Geoprocessing Tools',
                'btn_size': 30,
                'btns': [
                    ['mProcessingUserMenu_native:buffer', 0, 0],
                    ['mProcessingUserMenu_native:clip', 1, 0],
                    ['mProcessingUserMenu_native:convexhull', 0, 1],
                    ['mProcessingUserMenu_native:difference', 0, 2],
                    ['mProcessingUserMenu_native:dissolve', 0, 3],
                    ['mProcessingUserMenu_native:intersection', 1, 1],
                    ['mProcessingUserMenu_native:symmetricaldifference', 1, 2],
                    ['mProcessingUserMenu_native:union', 1, 3],
                    ['mProcessingUserMenu_qgis:eliminateselectedpolygons', 0, 4],
                ]
            },

            {
                'label': tr('Geometry Tools'),
                'id': 'Geometry Tools',
                'btn_size': 30,
                'btns': [
                    ['mProcessingUserMenu_native:centroids', 0, 0],
                    ['mProcessingUserMenu_native:collect', 0, 1],
                    ['mProcessingUserMenu_native:densifygeometries', 0, 2],
                    ['mProcessingUserMenu_native:extractvertices', 0, 3],
                    ['mProcessingUserMenu_native:multiparttosingleparts', 0, 4],
                    ['mProcessingUserMenu_native:polygonstolines', 0, 5],
                    ['mProcessingUserMenu_native:simplifygeometries', 1, 0],
                    ['mProcessingUserMenu_qgis:checkvalidity', 1, 1],
                    ['mProcessingUserMenu_qgis:delaunaytriangulation', 1, 2],
                    ['mProcessingUserMenu_qgis:exportaddgeometrycolumns', 1, 3],
                    ['mProcessingUserMenu_qgis:linestopolygons', 1, 4],
                    ['mProcessingUserMenu_qgis:voronoipolygons', 1, 5],
                ],
            },

            {
               'label': tr('Analysis Tools'),
               'id': 'Analysis Tools',
               'btn_size': 30,
               'btns': [
                   ['mProcessingUserMenu_native:countpointsinpolygon', 0, 0],
                   ['mProcessingUserMenu_native:lineintersections', 0, 1],
                   ['mProcessingUserMenu_native:meancoordinates', 0, 2],
                   ['mProcessingUserMenu_native:nearestneighbouranalysis', 0, 3],
                   ['mProcessingUserMenu_native:sumlinelengths', 1, 0],
                   ['mProcessingUserMenu_qgis:basicstatisticsforfields', 1, 1],
                   ['mProcessingUserMenu_qgis:distancematrix', 1, 2],
                   ['mProcessingUserMenu_qgis:listuniquevalues', 1, 3],
               ],
           },

            {
               'label': tr('Research Tools'),
               'id': 'Research Tools',
               'btn_size': 30,
               'btns': [
                   ['mProcessingUserMenu_native:creategrid', 0, 0],
                   ['mProcessingUserMenu_native:polygonfromlayerextent', 0, 1],
                   ['mProcessingUserMenu_native:randompointsinextent', 0, 2],
                   ['mProcessingUserMenu_native:randompointsinpolygons', 0, 3],
                   ['mProcessingUserMenu_native:randompointsonlines', 0, 4],
                   ['mProcessingUserMenu_native:selectbylocation', 0, 5],
                   ['mProcessingUserMenu_qgis:randompointsinlayerbounds', 1, 0],
                   ['mProcessingUserMenu_qgis:randompointsinsidepolygons', 1, 1],
                   ['mProcessingUserMenu_qgis:randomselection', 1, 2],
                   ['mProcessingUserMenu_qgis:randomselectionwithinsubsets', 1, 3],
                   ['mProcessingUserMenu_qgis:regularpoints', 1, 4],
               ],
           },

            {
               'label': tr('Data Management Tools'),
               'id': 'Data Management Tools',
               'btn_size': 30,
               'btns': [
                   ['mProcessingUserMenu_native:createspatialindex', 0, 0],
                   ['mProcessingUserMenu_native:joinattributesbylocation', 0, 1],
                   ['mProcessingUserMenu_native:mergevectorlayers', 0, 2],
                   ['mProcessingUserMenu_native:reprojectlayer', 1, 0],
                   ['mProcessingUserMenu_native:splitvectorlayer', 1, 1],
               ],
           },

        ]
    },

    {
        "tab_name": tr("Raster"),
        "tab_id": "Raster",
        "sections": [
            {
                'label': tr('Raster'),
                'id': 'Raster',
                'btn_size': 60,
                'btns': [
                    ['mActionShowRasterCalculator', 0, 0],
                    ['mActionShowGeoreferencer', 0, 1],
                    ['mActionShowAlignRasterTool', 0, 2],
                ],
            },

            {
                'label': tr('Raster analysis'),
                'id': 'Raster analysis',
                'btn_size': 30,
                'btns': [
                    ['mProcessingUserMenu_gdal:aspect', 0, 0],
                    ['mProcessingUserMenu_gdal:fillnodata', 0, 1],
                    ['mProcessingUserMenu_gdal:gridaverage', 0, 2],
                    ['mProcessingUserMenu_gdal:griddatametrics', 0, 3],
                    ['mProcessingUserMenu_gdal:gridinversedistance', 0, 4],
                    ['mProcessingUserMenu_gdal:gridnearestneighbor', 0, 5],
                    ['mProcessingUserMenu_gdal:hillshade', 0, 6],
                    ['mProcessingUserMenu_gdal:nearblack', 1, 0],
                    ['mProcessingUserMenu_gdal:proximity', 1, 1],
                    ['mProcessingUserMenu_gdal:roughness', 1, 2],
                    ['mProcessingUserMenu_gdal:sieve', 1, 3],
                    ['mProcessingUserMenu_gdal:slope', 1, 4],
                    ['mProcessingUserMenu_gdal:tpitopographicpositionindex', 1, 5],
                    ['mProcessingUserMenu_gdal:triterrainruggednessindex', 1, 6],
                ],
            },

            {
                'label': tr('Projections'),
                'id': 'Projections',
                'btn_size': 60,
                'btns': [
                    ['mProcessingUserMenu_gdal:warpreproject', 0, 0],
                    ['mProcessingUserMenu_gdal:assignprojection', 0, 1],
                    ['mProcessingUserMenu_gdal:extractprojection', 0, 2],
                ],
            },

            {
                'label': tr('Miscellaneous'),
                'id': 'Miscellaneous',
                'btn_size': 30,
                'btns': [
                    ['mProcessingUserMenu_gdal:buildvirtualraster', 0, 0],
                    ['mProcessingUserMenu_gdal:gdalinfo', 0, 1],
                    ['mProcessingUserMenu_gdal:merge', 0, 2],
                    ['mProcessingUserMenu_gdal:overviews', 1, 0],
                    ['mProcessingUserMenu_gdal:tileindex', 1, 1],
                ],
            },

            {
                'label': tr('Extract Projection'),
                'id': 'Extract Projection',
                'btn_size': 30,
                'btns': [
                    ['mProcessingUserMenu_gdal:cliprasterbyextent', 0, 0],
                    ['mProcessingUserMenu_gdal:cliprasterbymasklayer', 0, 1],
                    ['mProcessingUserMenu_gdal:contour', 1, 0],
                ],
            },

            {
               'label': tr('Conversion'),
               'id': 'Conversion',
               'btn_size': 30,
               'btns': [
                   ['mProcessingUserMenu_gdal:pcttorgb', 0, 0],
                   ['mProcessingUserMenu_gdal:rgbtopct', 0, 1],
                   ['mProcessingUserMenu_gdal:polygonize', 0, 2],
                   ['mProcessingUserMenu_gdal:rasterize', 1, 0],
                   ['mProcessingUserMenu_gdal:translate', 1, 1],
               ],
           },
        ]
    },

]
