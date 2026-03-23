import { defineStore } from "pinia";
import { ref, nextTick } from "vue";
import type { Anomaly, ExportRequest } from "@/services/types.ts";
import { exportData as exportDataService } from '@/services/export-service';

export const useExportStore = defineStore("export", () => {
    const selectedAnomalies = ref<Anomaly[]>([]);
    const exportRequest = ref<ExportRequest>({
        current_stream_stats: true,
        detections_summary: true,
        stats_summary: true,
        all_anomalies: true,
        selected_anomalies: false,
        no_anomalies: false,
        is_txt: true,
        is_json: false
    });
    const selectAllFlag = ref(false);
    const selectAllButtonFlag = ref(false);

    function initSelection() {
        selectedAnomalies.value = [];
        resetExportRequest();
    }

    function resetExportRequest() {
        exportRequest.value = {
            current_stream_stats: true,
            detections_summary: true,
            stats_summary: true,
            all_anomalies: true,
            selected_anomalies: false,
            no_anomalies: false,
            is_txt: true,
            is_json: false
        };
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
        selectAllFlag.value = false;  // reset first so watcher always fires
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