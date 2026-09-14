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
    val vm: SceneBuilderViewModel = viewModel(factory = SceneBuilderViewModelFactory())
    val state by vm.state.collectAsState()
    Scaffold(containerColor = DarkBlue) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Spacer(Modifier.width(6.dp)); Text("Back", color = PrimaryCyan) } }
            item { NeonHero("Scene Builder", "Compose consistent AI scenes from characters, locations, camera and mood.") }
            item { NeonSectionCard { Text("CHARACTERS", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(state.characters, key = { it.id }) { item -> FilterChip(selected = state.selectedCharacters.contains(item.id), onClick = { vm.toggleCharacter(item.id) }, label = { Text(item.name) }) } } } }
            item { NeonSectionCard { Text("LOCATION", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(state.locations, key = { it.id }) { item -> FilterChip(selected = state.selectedLocation == item.id, onClick = { vm.selectLocation(item.id) }, label = { Text(item.name) }) } } } }
            item { NeonSectionCard { Text("CAMERA", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(listOf("wide", "medium", "close_up", "low_angle", "high_angle")) { value -> FilterChip(selected = state.camera == value, onClick = { vm.setCamera(value) }, label = { Text(value) }) } } } }
            item { NeonSectionCard { Text("MOOD", color = PrimaryCyan); LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { items(listOf("action", "epic", "comedic", "tense", "peaceful", "sad")) { value -> FilterChip(selected = state.mood == value, onClick = { vm.setMood(value) }, label = { Text(value) }) } } } }
            if (state.error != null) item { Text(state.error!!, color = MaterialTheme.colorScheme.error) }
            item { Button(onClick = vm::compose, enabled = !state.loading && state.selectedCharacters.isNotEmpty(), modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { if (state.loading) CircularProgressIndicator(color = DarkBlue) else Text("🎨 Build Prompt") } }
            state.prompt?.let { prompt -> item { NeonSectionCard { Text("GENERATED PROMPT", color = PrimaryCyan); Text(prompt, color = TextLight, style = MaterialTheme.typography.bodySmall) } } }
        }
    }
}
