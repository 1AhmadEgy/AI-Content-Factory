package com.example.feature.scenes

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.core.theme.*

@Composable
fun SceneBuilderScreen(onBack: () -> Unit) {
    val vm: SceneBuilderViewModel = viewModel(factory = SceneBuilderViewModelFactory()); val state by vm.state.collectAsState()
    val cameraOptions = listOf("wide" to "واسعة", "medium" to "متوسطة", "close_up" to "قريبة", "low_angle" to "زاوية منخفضة", "high_angle" to "زاوية مرتفعة")
    val moodOptions = listOf("action" to "حركي", "epic" to "ملحمي", "comedic" to "كوميدي", "tense" to "متوتر", "peaceful" to "هادئ", "sad" to "حزين")
    Scaffold(containerColor = DarkBlue) { padding -> LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Spacer(Modifier.width(6.dp)); Text("رجوع", color = PrimaryCyan) } }
        item { NeonHero("منشئ المشاهد", "كوّن مشاهد متسقة بالذكاء الاصطناعي من الشخصيات والمواقع والكاميرا والمزاج.") }
        item { NeonSectionCard { Text("الشخصيات", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(state.characters, key = { it.id }) { item -> FilterChip(selected = state.selectedCharacters.contains(item.id), onClick = { vm.toggleCharacter(item.id) }, label = { Text(item.name) }) } } } }
        item { NeonSectionCard { Text("الموقع", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(state.locations, key = { it.id }) { item -> FilterChip(selected = state.selectedLocation == item.id, onClick = { vm.selectLocation(item.id) }, label = { Text(item.name) }) } } } }
        item { NeonSectionCard { Text("الكاميرا", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(cameraOptions) { (value, label) -> FilterChip(selected = state.camera == value, onClick = { vm.setCamera(value) }, label = { Text(label) }) } } } }
        item { NeonSectionCard { Text("المزاج", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(moodOptions) { (value, label) -> FilterChip(selected = state.mood == value, onClick = { vm.setMood(value) }, label = { Text(label) }) } } } }
        if (state.error != null) item { Text(state.error!!, color = MaterialTheme.colorScheme.error) }
        item { Button(onClick = vm::compose, enabled = !state.loading && state.selectedCharacters.isNotEmpty(), modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { if (state.loading) CircularProgressIndicator(color = DarkBlue) else Text("🎨 بناء الوصف") } }
        state.prompt?.let { prompt -> item { NeonSectionCard { Text("الوصف المُنشأ", color = PrimaryCyan); Text(prompt, color = TextLight, style = MaterialTheme.typography.bodySmall) } } }
    } }
}
