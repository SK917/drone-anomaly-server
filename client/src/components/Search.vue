<script setup lang="ts">
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import { ref, computed } from 'vue';
    import SearchCard from './SearchCard.vue';

    const anomaliesStore = useAnomaliesStore();
    const query = ref('');

    const filteredAnomalies = computed(() => {
        const q = query.value.toLowerCase().trim()

        if (!q) {
            return anomaliesStore.anomalies
        }

        return anomaliesStore.anomalies.filter((anomaly) => {
            const classMatch = anomaly.class_name?.toLowerCase().includes(q)

            const trackingMatch = anomaly.track_id
                ?.toString()
                .includes(q)

            return classMatch || trackingMatch
        })
    })

</script>

<template>
    <div class="flex flex-col gap-2 h-full min-h-0 pb-30 ml-4 mr-4">
        <div class="flex flex-row">
            <input
                v-model="query"
                class="border bg-slate-900 text-gray-200 font-orbit w-full outline-0 border-gray-700 p-2 rounded-sm focus:outline-yellow-600 focus:outline-2 hover:outline-gray-500 hover:outline-2"
                placeholder="Search by tracking ID or class name..."
            />
        </div>
        <div class="flex flex-row gap-6 justify-between">
            <div class="text-sm font-orbit text-gray-200">
                <span class="text-gray-400">Results: </span> {{ filteredAnomalies.length ?? 0}}
            </div>
        </div>
        <div class="grid grid-cols-3 lg:grid-cols-4 gap-2 content-start overflow-y-auto detections-scroll">
            <div v-if="filteredAnomalies.length===0" 
                class="col-span-3 lg:col-span-4 h-full flex items-center justify-center text-gray-400 text-lg font-orbit">
                    No anomalies.
            </div>
                    
            <SearchCard
                v-else
                v-for="anomaly in filteredAnomalies"
                :key="anomaly.track_id ?? anomaly.class_id"
                :anomaly="anomaly"
            />
        </div>
    </div>
</template>