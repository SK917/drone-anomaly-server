<script setup lang="ts">
    import { Crosshair, TriangleAlert, Gauge, Activity } from 'lucide-vue-next';

    interface Props {
        num: number;
        label: string;
        iconSelect: number;
    }
    const props = defineProps<Props>();

</script>

<template>
    <div class="p-2 flex items-end gap-2">
        <div class="flex items-center gap-2">
            <div v-if="iconSelect===1">
                <Crosshair :size="20" class="pr-1 text-lime-400" />
            </div>
            <div v-else-if="iconSelect===2">
                <TriangleAlert :size="20" class="pr-1 text-red-400" />
            </div>
            <div v-else-if="iconSelect===3">
                <Gauge :size="20" class="pr-1 text-amber-200" />
            </div>
            <div v-else-if="iconSelect===4">
                <Activity :size="20" class="pr-1 text-amber-200" />
            </div>
            <div class="text-gray-200 text-2xl font-tektur">
                {{ num }}
            </div>
        </div>
        <div class="text-gray-400 text-xs font-orbit">
            {{ label }}
        </div>
    </div>
</template>

<!--
<template>
    <div class="p-4 m-6 bg-sky-800 rounded-md outline-6 outline-blue-300">
        <div class="pb-2 text-amber-300 font-bold text-2xl text-center">
            {{ num }}
        </div>
        <div class="text-gray-200 text-sm text-center">
            {{ label }}
        </div>
    </div>

</template>
-->