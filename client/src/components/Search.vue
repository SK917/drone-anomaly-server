<script setup lang="ts">
    import { useAnomaliesStore } from '@/stores/anomalies-store';
    import { useExportStore } from '@/stores/export-store';
    import { ref, computed, watch } from 'vue';
    import SearchCard from './SearchCard.vue';
    import { ChevronUp, ChevronDown, Eraser, Square, SquareCheckBig } from 'lucide-vue-next';

    const anomaliesStore = useAnomaliesStore();
    const exportStore = useExportStore();
    const query = ref('');
    const minConfidence = ref(50);
    const maxConfidence = ref(100);
    const selectAll = ref(false);

    const toggleSelectAll = () => {
        selectAll.value = !selectAll.value;
        if(selectAll.value) {
            exportStore.selectAll(filteredAnomalies.value);
        } else {
            exportStore.deselectAll();
        }
    }

    watch(
        () => exportStore.selectAllButtonFlag,
        (val) => {
            selectAll.value = val;
        }
    );

    const filteredAnomalies = computed(() => {
        const raw = query.value.trim();
        const minVal = minConfidence.value;
        const maxVal = maxConfidence.value;
        const useMin = minVal >= 50 && minVal <= 100;
        const useMax = maxVal >= 50 && maxVal <= 100;

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

        return anomaliesStore.anomalies.filter((anomaly) => {
            const conf = (anomaly.confidence ?? 0) * 100;
            if (useMin && conf < minVal) return false;
            if (useMax && conf > maxVal) return false;
            if (orGroups.length === 0) return true;
            const searchText = `${anomaly.class_name ?? ''} ${anomaly.track_id ?? ''}`.toLowerCase();
            return orGroups.some(groupTerms =>
                groupTerms.every(conditionFn => conditionFn(searchText))
            );
        }).sort((a, b) => (a.track_id ?? 0) - (b.track_id ?? 0));
    });

    const clearFilters = () => {
        query.value = '';
        minConfidence.value = 50;
        maxConfidence.value = 100;
    }
</script>

<template>
    <div class="flex flex-col h-full min-h-0  sm: pb-4 md:pb-26 ml-4 mr-4">
        <div class="flex flex-row gap-2 items-center justify-between w-full">
            <div class="flex flex-row gap-2 items-center flex-1">
                <input
                    v-model="query"
                    class="border bg-slate-900 text-gray-200 font-orbit min-w-sm flex-1 outline-0 border-gray-700 p-2 rounded-sm focus:outline-yellow-600 focus:outline-2 hover:outline-gray-500 hover:outline-2"
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
            <div class="flex flex-row gap-2 items-center shrink-0">
                <button 
                    @click="toggleSelectAll"
                    class="flex flex-row gap-3 items-center cursor-pointer rounded-sm p-2 text-gray-400 border border-transparent
                    hover:border-yellow-600 hover:text-white font-orbit text-xs"
                >
                    <SquareCheckBig v-if="selectAll" :size="20" class="text-amber-200"/>
                    <Square v-else :size="20" class="text-amber-200"/>
                    Select All
                </button>
            </div>
        </div>
        <div class="flex flex-row gap-6 justify-between items-center">

            <div class="flex flex-row gap-0">
                <div class="flex gap-2 pr-4 items-center"> 
                    <div class="text-sm text-gray-400 font-orbit"><p>Minimum</p><p>Confidence:</p></div>
                    <div class="relative flex items-center bg-slate-900 border border-gray-700 rounded-sm min-h-9 group outline-2 outline-transparent
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
                    <div class="text-sm text-gray-400 font-orbit"><p>Maximum</p><p>Confidence:</p></div>
                    <div class="relative flex items-center bg-slate-900 border border-gray-700 rounded-sm min-h-9 group outline-2 outline-transparent
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
            <div class="text-md font-orbit font-bold text-amber-200 flex flex-row justify-end gap-10">
                <div>
                    <span class="inline-block min-w-8 text-right">{{ filteredAnomalies.length ?? 0}}</span><span class="text-gray-400 font-normal text-sm"> {{ filteredAnomalies.length === 1 ? ' Result' : ' Results' }}</span> 
                </div>
                <div class="pr-2">
                    <span class="inline-block min-w-8 text-right">{{ exportStore.selectedAnomalies.length ?? 0}}</span> <span class="text-gray-400 font-normal text-sm"> Selected</span> 
                </div>
            </div>
        </div>
        <div class="grid grid-cols-3 lg:grid-cols-4 gap-2 pr-4 content-start overflow-y-auto detections-scroll">
            <div v-if="filteredAnomalies.length===0" 
                class="col-span-3 lg:col-span-4 h-full pt-10 flex items-center justify-center text-gray-400 text-lg font-orbit">
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