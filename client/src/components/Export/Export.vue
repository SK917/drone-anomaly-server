<script setup lang="ts">
    import { ref, computed } from 'vue';
    import { useExportStore } from '@/stores/export-store';
    import { ArrowRightFromLine, X } from 'lucide-vue-next';
    import ExportFormItem from './ExportFormItem.vue';
    import type { ExportRequest } from '@/services/types';

    const exportStore = useExportStore();
    const viewExportPopup = ref(false);

    const toggleExportPopup = () => {
        viewExportPopup.value = !viewExportPopup.value;
    }

    const canExport = computed(() => {
        const req = exportStore.exportRequest;

        const hasAnomalyOption = req.all_anomalies || req.selected_anomalies || req.no_anomalies;
        if (!hasAnomalyOption) return false;

        if (req.no_anomalies) {
            if (!req.current_stream_stats && !req.detections_summary && !req.stats_summary) return false;
        }

        const hasFormat = req.is_txt || req.is_json;
        if (!hasFormat) return false;

        return true;
    });

    const exportData = () => {
        exportStore.exportData();
        toggleExportPopup();
    }

</script>

<template>
    <button 
        @click="toggleExportPopup"
        class="flex flex-row gap-3 items-center cursor-pointer bg-gray-800 rounded-sm p-2 text-gray-400 border border-transparent
        hover:border-yellow-600 hover:text-white font-orbit text-xs"
    >
        <ArrowRightFromLine :size=20 class="text-amber-200"/>
        Export to Log File
    </button>

    <Teleport to="body">
        <div
            v-show="viewExportPopup"
            class="fixed inset-0 z-100 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm"
        >
            <div class="bg-gray-900 border-2 border-gray-600 p-4 rounded-lg shadow-2xl max-w-lg w-full max-h-[95vh] m-2 flex flex-col gap-1 font-tektur overflow-y-auto detections-scroll">
                <div class="flex flex-row justify-end">
                    <button
                        @click="toggleExportPopup"
                        class="cursor-pointer text-gray-400 hover:text-amber-200 rounded-sm p-1"
                    >
                        <X :size=30 />
                    </button>
                </div>
                <div class="text-center flex flex-col gap-2">
                    <div class="text-3xl text-amber-200 uppercase">Export Log Data</div>
                    <div class="text-sm text-gray-400">Select what you'd like to include in your log, then click <span class="text-yellow-600 font-bold">Export</span> below.</div>
                </div>
                <div class="pt-6 flex flex-col gap-2">
                    <div class="text-xl text-yellow-600 font-semibold">General Statistics</div>
                    <ExportFormItem
                        field="current_stream_stats"
                        label="Current Stream Statistics"
                    />
                    <ExportFormItem
                        field="detections_summary"
                        label="Detections Summary"
                    />
                    <ExportFormItem
                        field="stats_summary"
                        label="Detections Statistics"
                    />
                </div>
                <div class="pt-6 flex flex-col gap-2">
                    <div class="flex flex-row gap-4 items-baseline">
                        <div class="text-xl text-yellow-600 font-semibold">Anomaly Data</div>
                        <div class="text-xs text-gray-400">*Select <span class="text-yellow-600 font-bold">one</span> option below.</div>
                    </div>
                    <ExportFormItem
                        field="all_anomalies"
                        label="All Anomalies"
                    />
                    <ExportFormItem
                        field="selected_anomalies"
                        label="Selected Anomalies"
                    />
                    <ExportFormItem
                        field="no_anomalies"
                        label="No Anomaly Data"
                    />
                </div>
                <div class="text-xs text-gray-400 mt-2">If you selected <span class="text-yellow-600 font-bold">No Anomaly Data</span>, you must choose at least one <span class="text-yellow-600 font-bold">General Statistic</span> to export.</div>

                <div class="pt-6 flex flex-col gap-2">
                    <div class="text-xl text-yellow-600 font-semibold">Log Type</div>
                    <div class="flex flex-row gap-6">
                        <ExportFormItem
                            field="is_json"
                            label="JSON File"
                        />
                        <ExportFormItem
                            field="is_txt"
                            label="Text File"
                        />
                    </div>
                </div>
                <button
                    @click="exportData"
                    :disabled="!canExport"
                    :class="canExport ? 'hover:border-amber-200 hover:text-gray-200 cursor-pointer' : 'opacity-40 cursor-not-allowed'"
                    class="w-full bg-gray-800 text-gray-400 border border-transparent text-xl font-bold py-2 mt-6 rounded uppercase"
                >
                    Export
                </button>

                <div class="text-sm text-yellow-600 mt-2 text-center font-bold uppercase">Disclaimer</div>
                <div class="text-xs text-gray-400 text-center">The stream does <span class="text-yellow-600 font-bold">not</span> pause while this menu is open.</div>
                <div class="text-xs text-gray-400 text-center">Because of this, you may see changes in the data.</div>
            </div>

        </div>
    </Teleport>
</template>