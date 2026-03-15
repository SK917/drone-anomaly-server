<script setup lang="ts">
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import { ref, computed } from 'vue';
    import SearchCard from './SearchCard.vue';
    import { ChevronUp, ChevronDown, Eraser } from 'lucide-vue-next';

    const anomaliesStore = useAnomaliesStore();
    const query = ref('');
    const minConfidence = ref(50);
    const maxConfidence = ref(100);

    const filteredAnomalies = computed(() => {
        const raw = query.value.trim();
        const minVal = minConfidence.value;
        const maxVal = maxConfidence.value;
        const useMin = minVal >= 50 && minVal <= 100;
        const useMax = maxVal >= 50 && maxVal <= 100;

        // Parse query for advanced search
        const orGroups = raw ? raw.split(/\bOR\b/i).map(g => {
            const terms = g.match(/"[^"]*"|-\S+|\S+/g) ?? [];
            return terms.map(term => {
                if (term.startsWith('"') && term.endsWith('"')) {
                    const phrase = term.slice(1, -1).toLowerCase();
                    return (text: string) => text.includes(phrase);
                } else if (term.startsWith('-')) {
                    const word = term.slice(1).toLowerCase();
                    return (text: string) => !text.includes(word);
                } else {
                    const word = term.toLowerCase();
                    return (text: string) => text.includes(word);
                }
            });
        }) : [];

        // Filter
        return anomaliesStore.anomalies.filter((anomaly) => {
            const conf = (anomaly.confidence ?? 0) * 100;
            if (useMin && conf < minVal) return false;
            if (useMax && conf > maxVal) return false;
            if (orGroups.length === 0) return true;
            const searchText = `${anomaly.class_name ?? ''} ${anomaly.track_id ?? ''}`.toLowerCase();
            return orGroups.some(groupTerms => 
                groupTerms.every(conditionFn => conditionFn(searchText))
            );
        });
    });

    const clearFilters = () => {
        query.value = '';
        minConfidence.value = 50;
        maxConfidence.value = 100;
    }

</script>

<template>
    <div class="flex flex-col h-full min-h-0  sm: pb-4 md:pb-30 ml-4 mr-4">
        <div class="flex flex-row gap-2 items-center">
            <input
                v-model="query"
                class="border bg-slate-900 text-gray-200 font-orbit w-full outline-0 border-gray-700 p-2 rounded-sm focus:outline-yellow-600 focus:outline-2 hover:outline-gray-500 hover:outline-2"
                placeholder="Search by tracking ID or class name..."
            />
            <button
                @click="clearFilters"
                title="Clear all filters"
                class="text-gray-400 cursor-pointer p-2 hover:text-gray-200"
            >
                <Eraser :size="24"/>
            </button>
        </div>
        <div class="flex flex-row gap-6 justify-between items-center">
            <div class="text-md font-orbit font-bold text-amber-200">
                <span class="text-gray-400 font-normal text-sm">Results: </span> {{ filteredAnomalies.length ?? 0}}
            </div>
            <div class="flex flex-row gap-0">
                <div class="flex gap-2 p-4 items-center"> 
                    <label class="text-sm text-gray-400 font-orbit">Minimum Confidence:</label>
                    <div class="relative flex items-center bg-gray-800 border border-gray-700 rounded-sm min-h-9 group outline-2 outline-transparent
                        has-[:focus]:outline-yellow-600 hover:not-has-[:focus]:outline-gray-500 focus-within:outline-yellow-600 transition-all">
                        <input 
                            type="number" 
                            v-model.number="minConfidence"
                            min="50" 
                            max="100" 
                            step="0.1"
                            class="bg-transparent text-gray-200 h-full w-16 focus:outline-none font-orbit no-spinner pl-2 text-md"
                        />
                        <div class="flex flex-col border-0 h-full w-6">
                            <button 
                                @click="minConfidence = Math.min(100, +(minConfidence + 0.1).toFixed(1))"
                                class="flex items-center justify-center flex-1 hover:bg-gray-700 text-gray-400 hover:text-amber-400"
                            >
                                <ChevronUp :size="16"/>
                            </button>
                            <button 
                                @click="minConfidence = Math.max(50, +(minConfidence - 0.1).toFixed(1))"
                                class="flex items-center justify-center flex-1 hover:bg-gray-700 text-gray-400 hover:text-amber-400"
                            >
                                <ChevronDown :size="16"/>
                            </button>
                        </div>
                    </div>
                    <label class="text-md text-gray-400 font-orbit">%</label>
                </div>
                <div class="flex gap-2 p-4 items-center"> 
                    <label class="text-sm text-gray-400 font-orbit">Maximum Confidence:</label>
                    <div class="relative flex items-center bg-gray-800 border border-gray-700 rounded-sm min-h-9 group outline-2 outline-transparent
                        has-[:focus]:outline-yellow-600 hover:not-has-[:focus]:outline-gray-500 focus-within:outline-yellow-600 transition-all">
                        <input 
                            type="number" 
                            v-model.number="maxConfidence"
                            min="50" 
                            max="100" 
                            step="0.1"
                            class="bg-transparent text-gray-200 h-full w-16 focus:outline-none font-orbit no-spinner pl-2 text-md"
                        />
                        <div class="flex flex-col border-0 h-full w-6">
                            <button 
                                @click="maxConfidence = Math.min(100, +(maxConfidence + 0.1).toFixed(1))"
                                class="flex items-center justify-center flex-1 hover:bg-gray-700 text-gray-400 hover:text-amber-400"
                            >
                                <ChevronUp :size="16"/>
                            </button>
                            <button 
                                @click="maxConfidence = Math.max(50, +(maxConfidence - 0.1).toFixed(1))"
                                class="flex items-center justify-center flex-1 hover:bg-gray-700 text-gray-400 hover:text-amber-400"
                            >
                                <ChevronDown :size="16"/>
                            </button>
                        </div>
                    </div>
                    <label class="text-md text-gray-400 font-orbit">%</label>
                </div>
            </div>
        </div>
        <div class="grid grid-cols-3 lg:grid-cols-4 gap-2 content-start overflow-y-auto detections-scroll">
            <div v-if="filteredAnomalies.length===0" 
                class="col-span-3 lg:col-span-4 h-full flex items-center justify-center text-gray-400 text-lg font-orbit">
                    No anomalies.
            </div>
                    
            <SearchCard
                v-else
                v-for="anomaly, index in filteredAnomalies"
                :key="anomaly.track_id ?? `idx-${index}`"
                :anomaly="anomaly"
            />
        </div>
    </div>
</template>