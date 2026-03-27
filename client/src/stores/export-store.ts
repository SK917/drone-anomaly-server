import { defineStore } from "pinia";
import { ref, watch, nextTick } from "vue";
import type { Anomaly, ExportRequest } from "@/services/types.ts";
import { exportData as exportDataService } from '@/services/export-service';
import { useAnomaliesStore } from "./anomalies-store";

export const useExportStore = defineStore("export", () => {
    const selectedAnomalies = ref<Anomaly[]>([]);
    const anomaliesStore = useAnomaliesStore();
    const hasAutoSwitchedToAll = ref(false);

    const getInitialExportState = () => {
        const hasAnomalies = anomaliesStore.anomalies.length > 0;
        return {
            current_stream_stats: true,
            detections_summary: true,
            stats_summary: true,
            all_anomalies: hasAnomalies,
            selected_anomalies: false,
            no_anomalies: !hasAnomalies,
            is_txt: true,
            is_json: false
        };
    };

    const exportRequest = ref<ExportRequest>(getInitialExportState());
    const selectAllFlag = ref(false);
    const selectAllButtonFlag = ref(false);

    watch(() => anomaliesStore.anomalies.length, (newCount) => {
        if (newCount > 0 && !hasAutoSwitchedToAll.value) {
            updateExportRequest('all_anomalies', true);
            hasAutoSwitchedToAll.value = true;
        } else if (newCount === 0) {
            hasAutoSwitchedToAll.value = false;
            updateExportRequest('no_anomalies', true);
        }
    });

    function initSelection() {
        selectedAnomalies.value = [];
        resetExportRequest();
    }

    function resetExportRequest() {
        exportRequest.value = getInitialExportState();
        hasAutoSwitchedToAll.value = false;
    }

    function updateExportRequest(field: keyof ExportRequest, value: boolean) {
        if (!exportRequest.value) return;
        
        const anomalyGroup: (keyof ExportRequest)[] = ['all_anomalies', 'selected_anomalies', 'no_anomalies'];
        const formatGroup: (keyof ExportRequest)[] = ['is_txt', 'is_json'];
        
        if (anomalyGroup.includes(field) && value === true) {
            anomalyGroup.forEach(f => exportRequest.value[f] = false);
        }
        
        if (formatGroup.includes(field) && value === true) {
            formatGroup.forEach(f => exportRequest.value[f] = false);
        }
        
        exportRequest.value[field] = value;
    }

    function selectAnomaly(anomaly: Anomaly) {
        selectedAnomalies.value.push(anomaly);
    }

    function deselectAnomaly(trackId: number) {
        selectedAnomalies.value = selectedAnomalies.value.filter(
            a => a.track_id !== trackId
        );
        selectAllButtonFlag.value = false;
    }

    function selectAll(anomalies: Anomaly[]) {
        const existingIds = new Set(selectedAnomalies.value.map(a => a.track_id));
        const newEntries = anomalies.filter(a => !existingIds.has(a.track_id));
        selectedAnomalies.value = [...selectedAnomalies.value, ...newEntries];
        selectAllFlag.value = false;
        nextTick(() => {
            selectAllFlag.value = true;
            selectAllButtonFlag.value = true;
        });
    }

    function deselectAll() {
        selectedAnomalies.value = [];
        selectAllFlag.value = false;
        selectAllButtonFlag.value = false;
    }

    function exportData() {
        exportDataService();
    }

    return {
        selectedAnomalies,
        selectAllFlag,
        selectAllButtonFlag,
        exportRequest,
        hasAutoSwitchedToAll,
        resetExportRequest,
        updateExportRequest,
        initSelection,
        selectAnomaly,
        deselectAnomaly,
        selectAll,
        deselectAll,
        exportData
    };
});