package com.example.feature

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.theme.*

@Composable
fun AIStudioScreen(onBack: () -> Unit = {}) {
    var prompt by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("مشهد") }
    var model by remember { mutableStateOf("Auto") }
    var style by remember { mutableStateOf("سينمائي") }
    var generating by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<String?>(null) }
    val types = listOf("نص", "سيناريو", "مشهد", "شخصية", "وصف صورة", "فكرة فيديو")
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Spacer(Modifier.width(6.dp)); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("AI Studio", "مساحة موحدة لإنشاء النصوص والمشاهد والشخصيات والمواد الإبداعية.") }
        item {
            NeonSectionCard {
                Text("ماذا تريد إنشاءه؟", color = PrimaryCyan, fontWeight = FontWeight.Bold)
                OutlinedTextField(
                    value = prompt,
                    onValueChange = { prompt = it },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 150.dp),
                    placeholder = { Text("اكتب فكرتك أو وصف المهمة…") },
                    minLines = 5
                )
            }
        }
        item {
            NeonSectionCard {
                Text("نوع المحتوى", color = PrimaryCyan, fontWeight = FontWeight.Bold)
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    types.forEach { item -> FilterChip(selected = type == item, onClick = { type = item }, label = { Text(item) }) }
                }
            }
        }
        item {
            NeonSectionCard {
                Text("إعدادات التوليد", color = PrimaryCyan, fontWeight = FontWeight.Bold)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { model = if (model == "Auto") "GPT" else "Auto" }, Modifier.weight(1f)) { Text("النموذج: $model") }
                    OutlinedButton(onClick = { style = if (style == "سينمائي") "واقعي" else "سينمائي" }, Modifier.weight(1f)) { Text(style) }
                }
            }
        }
        item {
            NeonActionButton(
                if (generating) "جاري التوليد…" else "✨ إنشاء",
                Modifier.fillMaxWidth(),
                enabled = prompt.isNotBlank() && !generating
            ) {
                generating = true
                result = "تم تجهيز طلب $type بأسلوب $style باستخدام $model.\n\nستظهر النتيجة هنا بعد اتصال محرك التوليد."
                generating = false
            }
        }
        if (generating) item { NeonProcessingState("جاري تجهيز التوليد…") }
        result?.let { value ->
            item {
                NeonSectionCard {
                    Text("النتيجة", color = PrimaryCyan, fontWeight = FontWeight.Bold)
                    Text(value, color = TextLight)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        NeonOutlinedButton("نسخ", onClick = {})
                        NeonOutlinedButton("حفظ", onClick = {})
                        NeonOutlinedButton("إعادة التوليد", onClick = {})
                    }
                }
            }
        }
    }
}

@Composable
fun SearchScreen(onBack: () -> Unit = {}) {
    var query by remember { mutableStateOf("") }
    val items = listOf("المشاريع", "المسلسلات", "الحلقات", "الشخصيات", "المشاهد", "التوليدات")
    val filtered = items.filter { query.isBlank() || it.contains(query, true) }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("البحث", "ابحث في مساحة الإنتاج والمحتوى والأصول.") }
        item { OutlinedTextField(query, { query = it }, Modifier.fillMaxWidth(), singleLine = true, leadingIcon = { Icon(Icons.Default.Search, null) }, placeholder = { Text("ابحث…") }) }
        items(filtered) { item -> NeonSectionCard { Row(verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Default.Search, null, tint = PrimaryCyan); Spacer(Modifier.width(12.dp)); Text(item, color = TextLight) } } }
        if (filtered.isEmpty()) item { NeonEmptyState("لا توجد نتائج", "جرّب كلمة بحث مختلفة.") }
    }
}

@Composable
fun NotificationsScreen(onBack: () -> Unit = {}) {
    val notifications = listOf("تم إنشاء شخصية جديدة", "اكتمل توليد المشهد 14", "الحلقة 03 قيد المعالجة", "فشل توليد سابق ويحتاج إلى إعادة المحاولة")
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("الإشعارات", "آخر أحداث الإنتاج والتوليد.") }
        items(notifications) { item -> NeonSectionCard { Text(item, color = TextLight); Text("الآن", color = TextMuted, style = MaterialTheme.typography.bodySmall) } }
    }
}

@Composable
fun SettingsScreen(onBack: () -> Unit = {}, onProviders: () -> Unit = {}, onBackend: () -> Unit = {}, onHelp: () -> Unit = {}) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("الإعدادات", "إدارة تجربة التطبيق والاتصال ومحركات الذكاء الاصطناعي.") }
        item { SettingsRow("مزودو الذكاء الاصطناعي", "النماذج والمزودون", onProviders) }
        item { SettingsRow("حالة Backend", "الصحة والاتصال", onBackend) }
        item { SettingsRow("الإشعارات", "تنبيهات التوليد والمهام") {} }
        item { SettingsRow("الخصوصية والبيانات", "إدارة البيانات المحلية") {} }
        item { SettingsRow("المظهر", "الوضع الداكن والهوية البصرية") {} }
        item { SettingsRow("المساعدة", "الدعم والأسئلة الشائعة", onHelp) }
        item { SettingsRow("حول AI Content Factory", "الإصدار والمعلومات") {} }
    }
}

@Composable
private fun SettingsRow(title: String, subtitle: String, onClick: () -> Unit) {
    NeonSectionCard {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) { Text(title, color = TextLight, fontWeight = FontWeight.Bold); Text(subtitle, color = TextMuted, style = MaterialTheme.typography.bodySmall) }
            IconButton(onClick = onClick) { Icon(Icons.Default.ChevronRight, null, tint = PrimaryCyan) }
        }
    }
}

@Composable
fun ProviderSettingsScreen(onBack: () -> Unit = {}) {
    val providers = listOf("OpenAI" to true, "Gemini" to true, "Local / Custom" to false)
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("مزودو الذكاء الاصطناعي", "إدارة المزودين والنماذج المستخدمة في التوليد.") }
        items(providers) { (name, active) -> NeonSectionCard { Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { Column(Modifier.weight(1f)) { Text(name, color = TextLight, fontWeight = FontWeight.Bold); Text(if (active) "متاح" else "غير مهيأ", color = TextMuted) }; NeonStatusChip(if (active) "متصل" else "غير مهيأ", active) } } }
        item { NeonEmptyState("الأسرار لا تُعرض هنا", "تتم قراءة مفاتيح المزود من إعدادات البيئة/الخادم ولا ينبغي تخزينها داخل الواجهة.") }
    }
}

@Composable
fun BackendStatusScreen(onBack: () -> Unit = {}) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("حالة Backend", "مراقبة صحة الخدمة والاتصال والعمال.") }
        item { NeonMetricCard("الحالة", "Online", "واجهة المراقبة تعرض الحالة اللحظية من Control Center") }
        item { NeonMetricCard("Workers", "3", "Running / Idle") }
        item { NeonMetricCard("Queue", "—", "تظهر التفاصيل الحية في مركز التحكم") }
        item { NeonProcessingState("المزامنة اللحظية", .72f) }
    }
}

@Composable
fun GenerationHistoryScreen(onBack: () -> Unit = {}) {
    val history = listOf("Scene 14 • Success", "Character • Success", "Episode 03 • Processing", "Scene 11 • Failed")
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("سجل التوليد", "كل طلبات إنشاء المحتوى وحالاتها.") }
        items(history) { entry -> NeonSectionCard { Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { Text(entry, Modifier.weight(1f), color = TextLight); NeonStatusChip(if (entry.endsWith("Failed")) "فشل" else "حالة محفوظة", !entry.endsWith("Failed")) } } }
    }
}

@Composable
fun HelpAboutScreen(onBack: () -> Unit = {}) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("المساعدة وحول التطبيق", "مرجع سريع لاستخدام AI Content Factory.") }
        item { NeonSectionCard { Text("إنشاء المحتوى", color = PrimaryCyan, fontWeight = FontWeight.Bold); Text("استخدم AI Studio لوصف المهمة، ثم راجع النتيجة واحفظها أو أعد توليدها.", color = TextLight) } }
        item { NeonSectionCard { Text("Scene Builder", color = PrimaryCyan, fontWeight = FontWeight.Bold); Text("اختر الشخصيات والموقع والكاميرا والمزاج لبناء وصف متسق للمشهد.", color = TextLight) } }
        item { NeonSectionCard { Text("الإصدار", color = PrimaryCyan, fontWeight = FontWeight.Bold); Text("AI Content Factory 1.0", color = TextLight) } }
    }
}
