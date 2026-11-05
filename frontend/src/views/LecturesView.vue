<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const mode = ref("list"); // list | view | edit | new
const lectures = ref([]);
const subjects = ref([]);
const filterSid = ref("");
const current = ref(null); // полная лекция в режиме view/edit
const imgUrls = ref({}); // attachmentId -> blobUrl
const busy = ref(false);
const err = ref("");

// форма создания/редактирования
const form = ref({ subject_id: "", date: "", pair_number: "", content_md: "" });
const fileInput = ref(null);

const todayIso = () => new Date().toISOString().slice(0, 10);
const dm = (s) => (s ? s.slice(8, 10) + "." + s.slice(5, 7) + "." + s.slice(0, 4) : "");

async function loadSubjects() {
  subjects.value = await api.get("/subjects");
}
async function loadList() {
  const q = filterSid.value ? `?subject_id=${filterSid.value}` : "";
  lectures.value = await api.get("/lectures" + q);
}

function revokeImgs() {
  for (const u of Object.values(imgUrls.value)) URL.revokeObjectURL(u);
  imgUrls.value = {};
}

async function open(id) {
  err.value = "";
  revokeImgs();
  current.value = await api.get(`/lectures/${id}`);
  mode.value = "view";
  for (const a of current.value.attachments) {
    if (a.kind === "photo") {
      try {
        imgUrls.value[a.id] = await api.blobUrl(a.url);
      } catch {
        /* пропускаем битые */
      }
    }
  }
}

function startNew() {
  err.value = "";
  form.value = {
    subject_id: subjects.value[0]?.id ?? "",
    date: todayIso(),
    pair_number: "",
    content_md: "",
  };
  mode.value = "new";
}

function startEdit() {
  form.value = {
    subject_id: current.value.subject_id,
    date: current.value.date,
    pair_number: current.value.pair_number ?? "",
    content_md: current.value.content_md,
  };
  mode.value = "edit";
}

function backToList() {
  revokeImgs();
  current.value = null;
  mode.value = "list";
  loadList();
}

async function save() {
  if (!form.value.subject_id) {
    err.value = "Выберите предмет";
    return;
  }
  busy.value = true;
  err.value = "";
  const payload = {
    subject_id: Number(form.value.subject_id),
    date: form.value.date || todayIso(),
    pair_number: form.value.pair_number ? Number(form.value.pair_number) : null,
    content_md: form.value.content_md,
  };
  try {
    if (mode.value === "new") {
      const created = await api.post("/lectures", payload);
      await open(created.id);
    } else {
      await api.patch(`/lectures/${current.value.id}`, payload);
      await open(current.value.id);
    }
  } catch (e) {
    err.value = e.message || "Ошибка сохранения";
  } finally {
    busy.value = false;
  }
}

async function removeLecture() {
  if (!confirm("Удалить лекцию вместе с вложениями?")) return;
  await api.del(`/lectures/${current.value.id}`);
  backToList();
}

async function removeAttachment(a) {
  if (!confirm("Удалить вложение?")) return;
  await api.del(`/lectures/attachments/${a.id}`);
  await open(current.value.id);
}

async function onFile(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  busy.value = true;
  try {
    await api.upload(`/lectures/${current.value.id}/attachments`, file);
    await open(current.value.id);
  } catch (err2) {
    err.value = err2.message || "Не удалось загрузить";
  } finally {
    busy.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

async function download(a) {
  try {
    const url = await api.blobUrl(a.url);
    const link = document.createElement("a");
    link.href = url;
    link.download = a.original_name || "file";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch {
    err.value = "Файл недоступен";
  }
}

const empty = computed(() => mode.value === "list" && !lectures.value.length);

onMounted(() => {
  loadSubjects();
  loadList();
});
onUnmounted(revokeImgs);
</script>

<template>
  <!-- ===== Список ===== -->
  <template v-if="mode === 'list'">
    <div class="page-head">
      <div>
        <h1 class="t-h1">Лекции</h1>
        <div v-if="lectures.length" class="muted sub">{{ lectures.length }} записей</div>
      </div>
      <button class="btn btn-primary" @click="startNew"><Icon name="plus" :size="16" /> Новая</button>
    </div>

    <div class="filterbar">
      <select v-model="filterSid" class="sel" @change="loadList" aria-label="Фильтр по предмету">
        <option value="">Все предметы</option>
        <option v-for="su in subjects" :key="su.id" :value="su.id">{{ su.name }}</option>
      </select>
    </div>

    <div v-if="empty" class="empty">
      <strong>Пока нет лекций</strong>
      Записывай через бота (кнопка «Лекция») или создай здесь.
    </div>

    <div v-else class="list">
      <button v-for="l in lectures" :key="l.id" class="lecrow" @click="open(l.id)">
        <div class="lecmain">
          <div class="lectop">
            <span class="tag">{{ l.subject_name }}</span>
            <span class="mono date">{{ dm(l.date) }}</span>
            <span v-if="l.pair_number" class="muted pair">· {{ l.pair_number }} пара</span>
          </div>
          <div class="preview">{{ l.preview || "— без текста —" }}</div>
        </div>
        <div class="lecmeta">
          <span v-if="l.attachments" class="att"><Icon name="image" :size="14" /> {{ l.attachments }}</span>
          <Icon name="chevronR" :size="16" />
        </div>
      </button>
    </div>
  </template>

  <!-- ===== Просмотр ===== -->
  <template v-else-if="mode === 'view' && current">
    <div class="page-head">
      <button class="icon-btn ghost" aria-label="Назад" @click="backToList"><Icon name="arrowLeft" :size="18" /></button>
      <div class="headmid">
        <div class="lectop">
          <span class="tag">{{ current.subject_name }}</span>
          <span class="mono date">{{ dm(current.date) }}</span>
          <span v-if="current.pair_number" class="muted pair">· {{ current.pair_number }} пара</span>
        </div>
      </div>
      <div class="acts">
        <button class="icon-btn" aria-label="Редактировать" @click="startEdit"><Icon name="editor" :size="16" /></button>
        <button class="icon-btn danger" aria-label="Удалить" @click="removeLecture"><Icon name="trash" :size="16" /></button>
      </div>
    </div>

    <div v-if="err" class="err">{{ err }}</div>

    <div v-if="current.content_md" class="prose card">{{ current.content_md }}</div>
    <div v-else class="muted nocontent">Текста нет — только вложения.</div>

    <div v-if="current.attachments.length" class="attachments">
      <h2 class="t-label">Вложения</h2>
      <div class="attgrid">
        <div v-for="a in current.attachments" :key="a.id" class="attcard">
          <img v-if="a.kind === 'photo' && imgUrls[a.id]" :src="imgUrls[a.id]" :alt="a.original_name || 'фото'" @click="download(a)" />
          <button v-else class="doc" @click="download(a)">
            <Icon name="file" :size="20" />
            <span class="docname">{{ a.original_name || "файл" }}</span>
          </button>
          <button class="att-del icon-btn sm danger" aria-label="Удалить вложение" @click="removeAttachment(a)"><Icon name="trash" :size="13" /></button>
        </div>
      </div>
    </div>

    <label class="addatt">
      <input ref="fileInput" type="file" hidden @change="onFile" />
      <span class="btn btn-ghost" :class="{ disabled: busy }"><Icon name="plus" :size="15" /> {{ busy ? "Загрузка…" : "Добавить вложение" }}</span>
    </label>
  </template>

  <!-- ===== Создание / редактирование ===== -->
  <template v-else>
    <div class="page-head">
      <button class="icon-btn ghost" aria-label="Назад" @click="mode === 'edit' ? open(current.id) : backToList()"><Icon name="arrowLeft" :size="18" /></button>
      <h1 class="t-h1">{{ mode === "new" ? "Новая лекция" : "Редактирование" }}</h1>
      <span />
    </div>

    <div v-if="err" class="err">{{ err }}</div>

    <form class="editform card" @submit.prevent="save">
      <div class="row">
        <div class="field">
          <label>Предмет</label>
          <select v-model="form.subject_id" class="sel">
            <option v-for="su in subjects" :key="su.id" :value="su.id">{{ su.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>Дата</label>
          <input v-model="form.date" type="date" class="mono" />
        </div>
        <div class="field narrow">
          <label>Пара</label>
          <input v-model="form.pair_number" type="number" min="1" max="8" placeholder="—" class="mono" />
        </div>
      </div>
      <div class="field">
        <label>Текст (Markdown)</label>
        <textarea v-model="form.content_md" rows="14" placeholder="Конспект лекции…"></textarea>
      </div>
      <div class="formacts">
        <button type="button" class="btn btn-ghost" @click="mode === 'edit' ? open(current.id) : backToList()">Отмена</button>
        <button class="btn btn-primary" :disabled="busy">{{ busy ? "Сохраняю…" : "Сохранить" }}</button>
      </div>
    </form>
  </template>
</template>

<style scoped>
.sub {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
}
.filterbar {
  margin-bottom: var(--space-5);
}
.sel {
  max-width: 260px;
}
.list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.lecrow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  width: 100%;
  text-align: left;
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: inherit;
  transition: border-color var(--dur-fast) var(--ease-standard);
}
.lecrow:hover {
  border-color: var(--color-border-strong);
}
.lecmain {
  min-width: 0;
}
.lectop {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.tag {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-accent-soft, var(--color-sunken));
  color: var(--color-accent);
}
.date {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
.pair {
  font-size: var(--text-xs);
}
.preview {
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.lecmeta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
.att {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
}
.headmid {
  flex: 1;
  min-width: 0;
}
.acts {
  display: flex;
  gap: var(--space-2);
}
.prose {
  padding: var(--space-5);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: var(--text-base);
  line-height: 1.7;
}
.nocontent {
  padding: var(--space-4) 0;
  font-size: var(--text-sm);
}
.attachments {
  margin-top: var(--space-6);
}
.attgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-3);
}
.attcard {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}
.attcard img {
  display: block;
  width: 100%;
  height: 120px;
  object-fit: cover;
  cursor: zoom-in;
}
.doc {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  height: 120px;
  padding: var(--space-3);
  background: var(--color-sunken);
  color: var(--color-text-secondary);
  cursor: pointer;
  border: none;
}
.docname {
  font-size: var(--text-xs);
  text-align: center;
  overflow-wrap: anywhere;
  line-clamp: 2;
}
.att-del {
  position: absolute;
  top: 4px;
  right: 4px;
  background: color-mix(in srgb, var(--color-bg) 70%, transparent);
  backdrop-filter: blur(2px);
}
.addatt {
  display: inline-block;
  margin-top: var(--space-5);
  cursor: pointer;
}
.addatt .disabled {
  opacity: 0.6;
  pointer-events: none;
}
.editform {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.editform .row {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.editform .field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
}
.editform .field label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
.editform .field.narrow {
  max-width: 90px;
  flex: 0 0 auto;
}
textarea {
  width: 100%;
  resize: vertical;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
}
.formacts {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}
.err {
  color: var(--color-danger);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}
.ghost {
  background: transparent;
  border-color: transparent;
}

@media (max-width: 759px) {
  .sel {
    max-width: none;
    width: 100%;
  }
}
</style>
