<script setup lang="ts">
    import { ref, computed } from 'vue';
    import { useSocketStore } from '@/stores/socket-store';
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import { useDetectionsStore } from '@/stores/detections-store';
    import { useExportStore } from '@/stores/export-store';
    import { useAnalyticsStore } from '@/stores/analytics-store';
    import { Settings, X, Info } from 'lucide-vue-next';
    import AnomalyClassFormItem from './AnomalyClassFormItem.vue';

    const socketStore = useSocketStore();
    const anomaliesStore = useAnomaliesStore();
    const detectionsStore = useDetectionsStore();
    const exportStore = useExportStore();
    const analyticsStore = useAnalyticsStore();
    const viewSettingsPopup = ref(false);

    const standardClasses = computed(() => 
        anomaliesStore.selectedClasses.filter(item => !item.suggested_as_anomaly)
    );

    const anomalyClasses = computed(() => 
        anomaliesStore.selectedClasses.filter(item => item.suggested_as_anomaly)
    );

    const toggleSettingsPopup = () => {
        viewSettingsPopup.value = !viewSettingsPopup.value;
    }

    const applyUpdates = () => {
        socketStore.send({
            type: "UPDATE_ANOMALY_CLASSES",
            classes: anomaliesStore.selectedClasses.filter(c => c.selected).map(c => c.class_name)
        })

        anomaliesStore.resetAnomalies();
        detectionsStore.resetCounts();
        exportStore.resetExportRequest();
        analyticsStore.resetAnalytics();

        toggleSettingsPopup();
    }

</script>

<template>
    <button 
        @click="toggleSettingsPopup"
        class="flex flex-row gap-3 w-45 items-center cursor-pointer bg-gray-800 rounded-sm p-2 text-gray-400 border border-transparent
        hover:border-yellow-600 hover:text-white font-orbit text-xs"
    >
        <Settings :size=20 class="text-amber-200"/>
        Anomaly Settings
    </button>

    <Teleport to="body">
        <div
            v-show="viewSettingsPopup"
            class="fixed inset-0 z-100 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm"
        >
            <div class="bg-gray-900 border-2 border-gray-600 p-4 rounded-lg shadow-2xl max-w-lg w-full max-h-[95vh] m-2 flex flex-col gap-1 font-tektur overflow-y-auto detections-scroll">
                <div class="flex flex-row justify-end">
                    <button
                        @click="toggleSettingsPopup"
                        class="cursor-pointer text-gray-400 hover:text-amber-200 rounded-sm p-1"
                    >
                        <X :size=30 />
                    </button>
                </div>
                <div class="flex flex-col gap-2">
                    <div class="text-center text-3xl text-amber-200 uppercase">Anomaly Class Settings</div>
                    <div class="text-center text-sm text-gray-400">Select what classes should be considered as <span class="text-red-500 font-bold">anomalies</span>, then click <span class="text-yellow-600 font-bold">Confirm</span> below.</div>
                    <br>
                    <div class="text-sm text-gray-400 flex flex-row gap-2">
                        <Info :size="20" class="text-amber-200"/>
                        <div>If an item is <span class="text-lime-400 font-semibold">unchecked</span>, it is considered an <span class="text-lime-400 font-semibold">object</span>.</div>
                        
                    </div>
                    <div class="text-sm text-gray-400 flex flex-row gap-2">
                        <Info :size="20" class="text-amber-200"/>
                        <div>If an item is <span class="text-red-400 font-semibold">checked</span>, it is considered an <span class="text-red-400 font-semibold">anomaly</span>.</div>
                        
                    </div>
                </div>
                <div class="flex flex-row gap-10">
                    <div class="pt-6 flex flex-col gap-2">
                        <div class="text-xl text-yellow-600 font-semibold">Suggested Objects</div>
                        <div 
                            v-for="item in standardClasses"
                            :key="item.class_id"
                        >
                            <AnomalyClassFormItem :id="item.class_id"/>
                        </div>
                    </div>
                    <div class="pt-6 flex flex-col gap-2">
                        <div class="text-xl text-yellow-600 font-semibold">Suggested Anomalies</div>
                        <div 
                            v-for="item in anomalyClasses"
                            :key="item.class_id"
                        >
                            <AnomalyClassFormItem :id="item.class_id"/>
                        </div>
                    </div>
                </div>
                
                <button
                    @click="applyUpdates"
                    class="w-full bg-gray-800 text-gray-400 border border-transparent text-xl font-bold py-2 mt-6 rounded uppercase hover:border-amber-200 hover:text-gray-200 cursor-pointer"
                >
                    Confirm
                </button>

                <div class="text-md text-yellow-600 mt-2 text-center font-bold uppercase">Warning</div>
                <div class="text-xs text-gray-400 text-center">Updating anomaly classes will cause all data to be <span class="text-yellow-600 font-bold">reset</span>.</div>
                <div class="text-xs text-gray-400 text-center">Please export any data you'd like to keep before making your changes.</div>
            </div>

        </div>
    </Teleport>
</template>