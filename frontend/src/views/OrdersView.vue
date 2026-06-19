<template>
  <section>
    <PageHeader eyebrow="Orders" title="采购订单管理">
      <button class="primary-btn" @click="submitOrder">创建订单</button>
    </PageHeader>

    <section class="form-panel">
      <div class="form-grid">
        <label>
          订单号
          <input v-model="form.orderNo" />
        </label>
        <label>
          供应商
          <select v-model.number="form.supplierId">
            <option disabled :value="null">选择供应商</option>
            <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
              {{ supplier.name }}
            </option>
          </select>
        </label>
        <label>
          预计到货
          <input v-model="form.expectedDate" type="date" />
        </label>
        <label>
          备注
          <input v-model="form.remark" />
        </label>
      </div>

      <div class="line-editor">
        <select v-model.number="line.ingredientId" @change="onIngredientChange">
          <option disabled :value="null">选择原料</option>
          <option v-for="item in ingredients" :key="item.id" :value="item.id">
            {{ item.name }} / {{ item.unit }}
          </option>
        </select>
        <input v-model.number="line.quantity" type="number" min="1" placeholder="数量" />
        <input v-model.number="line.unitPrice" type="number" min="0" placeholder="单价" @input="checkPrice" />
        <span class="avg-price-hint" v-if="line.referenceAvgPrice !== null">
          参考均价: ¥{{ line.referenceAvgPrice.toFixed(2) }}
        </span>
        <button class="secondary-btn" @click="addLine">添加明细</button>
      </div>
      <div v-if="priceWarning" class="price-warning">
        ⚠️ 当前单价高于参考均价 10%，已标记为异常高价
      </div>

      <DataTable :columns="lineColumns" :rows="form.items" :rowClass="rowClass">
        <template #ingredientName="{ row }">{{ ingredientName(row.ingredientId) }}</template>
        <template #referenceAvgPrice="{ row }">
          {{ row.referenceAvgPrice !== null ? '¥' + row.referenceAvgPrice.toFixed(2) : '-' }}
        </template>
        <template #amount="{ row }">¥{{ (row.quantity * row.unitPrice).toFixed(2) }}</template>
        <template #isOverpriced="{ row }">
          <span v-if="row.isOverpriced" class="overpriced-badge">⚠️ 异常高价</span>
          <span v-else class="normal-badge">正常</span>
        </template>
      </DataTable>

      <div class="total-row">
        <span>订单总额：</span>
        <span class="total-amount">¥{{ totalAmount.toFixed(2) }}</span>
      </div>
    </section>

    <DataTable :columns="columns" :rows="orders">
      <template #status="{ row }">
        <select :value="row.status" @change="changeStatus(row, $event.target.value)">
          <option value="draft">草稿</option>
          <option value="approved">已审批</option>
          <option value="received">已到货</option>
          <option value="cancelled">已取消</option>
        </select>
      </template>
      <template #totalAmount="{ row }">¥{{ row.totalAmount.toFixed(2) }}</template>
      <template #hasOverpriced="{ row }">
        <span v-if="row.items && row.items.some(i => i.isOverpriced)" class="overpriced-badge">
          ⚠️ 含高价
        </span>
        <span v-else class="normal-badge">正常</span>
      </template>
    </DataTable>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { inventoryApi } from '../api/inventory'
import { ordersApi } from '../api/orders'
import DataTable from '../components/DataTable.vue'
import PageHeader from '../components/PageHeader.vue'

const orders = ref([])
const suppliers = ref([])
const ingredients = ref([])
const priceWarning = ref(false)
const form = reactive({
  orderNo: `PO${new Date().toISOString().slice(0, 10).replaceAll('-', '')}001`,
  supplierId: null,
  expectedDate: '',
  remark: '',
  items: []
})
const line = reactive({
  ingredientId: null,
  quantity: 1,
  unitPrice: 0,
  referenceAvgPrice: null,
  isOverpriced: false
})

const columns = [
  { key: 'orderNo', label: '订单号' },
  { key: 'supplierName', label: '供应商' },
  { key: 'expectedDate', label: '预计到货' },
  { key: 'status', label: '状态' },
  { key: 'hasOverpriced', label: '价格异常' },
  { key: 'totalAmount', label: '金额' }
]
const lineColumns = [
  { key: 'ingredientName', label: '原料' },
  { key: 'quantity', label: '数量' },
  { key: 'referenceAvgPrice', label: '参考均价' },
  { key: 'unitPrice', label: '单价' },
  { key: 'amount', label: '小计' },
  { key: 'isOverpriced', label: '状态' }
]

const totalAmount = computed(() => {
  return form.items.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0)
})

function ingredientName(id) {
  return ingredients.value.find((item) => item.id === id)?.name || '-'
}

function rowClass(row) {
  return row.isOverpriced ? 'overpriced-row' : ''
}

async function onIngredientChange() {
  line.referenceAvgPrice = null
  line.isOverpriced = false
  priceWarning.value = false
  if (line.ingredientId) {
    try {
      const res = await ordersApi.getAvgPrice(line.ingredientId)
      line.referenceAvgPrice = res.data.avgPrice
      checkPrice()
    } catch (e) {
      console.error('获取均价失败', e)
    }
  }
}

function checkPrice() {
  if (line.referenceAvgPrice && line.unitPrice > line.referenceAvgPrice * 1.1) {
    line.isOverpriced = true
    priceWarning.value = true
  } else {
    line.isOverpriced = false
    priceWarning.value = false
  }
}

function addLine() {
  if (!line.ingredientId || !line.quantity) return
  form.items.push({
    id: Date.now(),
    ingredientId: line.ingredientId,
    quantity: line.quantity,
    unitPrice: line.unitPrice,
    referenceAvgPrice: line.referenceAvgPrice,
    isOverpriced: line.isOverpriced
  })
  Object.assign(line, {
    ingredientId: null,
    quantity: 1,
    unitPrice: 0,
    referenceAvgPrice: null,
    isOverpriced: false
  })
  priceWarning.value = false
}

async function loadOrders() {
  const res = await ordersApi.list()
  orders.value = res.data
}

async function submitOrder() {
  if (!form.supplierId || !form.items.length) return
  const payload = {
    ...form,
    items: form.items.map(({ id, ...rest }) => rest)
  }
  await ordersApi.create(payload)
  Object.assign(form, {
    orderNo: `PO${new Date().toISOString().slice(0, 10).replaceAll('-', '')}${Date.now()
      .toString()
      .slice(-3)}`,
    supplierId: null,
    expectedDate: '',
    remark: '',
    items: []
  })
  await loadOrders()
}

async function changeStatus(order, status) {
  await ordersApi.updateStatus(order.id, status)
  await loadOrders()
}

onMounted(async () => {
  const [optionsRes] = await Promise.all([inventoryApi.options(), loadOrders()])
  ingredients.value = optionsRes.data.ingredients
  suppliers.value = optionsRes.data.suppliers
})
</script>

<style scoped>
.line-editor {
  display: flex;
  gap: 12px;
  align-items: center;
  margin: 16px 0;
  flex-wrap: wrap;
}

.line-editor select,
.line-editor input {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
}

.line-editor input[type="number"] {
  width: 100px;
}

.avg-price-hint {
  font-size: 13px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 10px;
  border-radius: 4px;
}

.price-warning {
  background: #fef3c7;
  color: #92400e;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 14px;
  border: 1px solid #fcd34d;
}

.overpriced-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.normal-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #d1fae5;
  color: #065f46;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

:deep(.overpriced-row) {
  background: #fef2f2 !important;
}

.total-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-top: 8px;
  background: #f9fafb;
  border-top: 2px solid #e5e7eb;
  font-size: 16px;
  font-weight: 600;
}

.total-amount {
  color: #dc2626;
  font-size: 20px;
}
</style>
