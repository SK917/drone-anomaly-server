<script setup lang="ts">
    import { computed } from 'vue';

    interface Props {
        num: number
        label: String
        otherInfo: String
        isPercent: boolean
    }

    const props = defineProps<Props>();
    const numFixed = computed(() => {
        const baseValue = props.isPercent ? props.num * 100 : props.num;
        return baseValue.toFixed(2);
    }) 

</script>

<template>
    <div class="flex flex-col items-center justify-between m-2 p-4 w-auto min-w-40 min-h-32 border border-gray-600 rounded-sm
        hover:border-yellow-600">
        <div class="text-4xl text-amber-200">
            <span v-if="isPercent">
                {{ numFixed }}%
            </span>
            <span v-else>
                {{ num }}
            </span>
        </div>
        <div v-if="otherInfo !== null" class="text-gray-400 text-sm">
            {{ otherInfo }}
        </div>
        <div class="text-white text-md pt-2">
            {{ label }}
        </div>
    </div>

</template>