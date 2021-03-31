from .utils import tr


RIBBON_DEFAULT = [
    {
        "tab_name": tr("Main"),
        "tab_id": 'Main',
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
                'label': tr('Measures'),
                'btn_size': 30,
                'btns': [
                    ['mActionMeasure', 0, 0],
                    ['mActionMeasureArea', 0, 1],
                    ['mActionMeasureAngle', 1, 0],
                ],
            },

            {
                'label': tr('Layers'),
                'btn_size': 30,
                'btns': [
                    ['mActionAddOgrLayer', 0, 0],
                    ['mActionAddWmsLayer', 0, 1],
                    ['mActionAddPgLayer', 0, 2],
                    ['mActionAddMeshLayer', 0, 3],
                    ['mActionAddWcsLayer', 0, 4],
                    ['mActionAddDelimitedText', 0, 5],

                    ['mActionAddRasterLayer', 1, 0],
                    ['mActionAddWfsLayer', 1, 1],
                    ['mActionAddSpatiaLiteLayer', 1, 2],
                    ['mActionAddVirtualLayer', 1, 3],
                    ['mActionNewMemoryLayer', 1, 4],
                ],
            },

        ]
    },

    {
        "tab_name": tr("Tools"),
        "tab_id": "Tools",
        "sections": [
            {
                'label': tr('Adv. Attributes'),
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
                'label': tr('Digitalization'),
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
        "tab_name": tr("GIAP Tools"),
        "tab_id": "GIAP Tools",
        "sections": [
            {
                'label': tr('Prints'),
                'id': 'Prints',
                'btn_size': 30,
                'btns': [
                    ['mActionNewPrintLayout', 0, 0],
                    ['giapMyPrints', 0, 1],
                    ['mActionShowLayoutManager', 1, 0],
                    ['giapQuickPrint', 1, 1],
                ]
            },

            {
                'label': tr('GIAP Tools'),
                'id': 'GIAP Tools',
                'btn_size': 60,
                'btns': [
                    ['giapCompositions', 0, 0],
                    ['giapWMS', 0, 1],
                    ['giapWWWSite', 0, 2],
                ]
            },

        ]
    },

]
