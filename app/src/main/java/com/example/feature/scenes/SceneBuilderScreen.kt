package com.example.feature.scenes

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SceneBuilderScreen(onBack: () -> Unit) {
    val vm: SceneBuilderViewModel = viewModel(factory = SceneBuilderViewModelFactory())
    val state by vm.state.collectAsState()
    Scaffold(topBar = {
        TopAppBar(title = { Text("بناء مشهد حقيقي") }, navigationIcon = {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = "رجوع") }
        })
    }) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text("الشخصيات", style = MaterialTheme.typography.titleMedium)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(horizontal = 2.dp)) {
                items(state.characters, key = { it.id }) { item ->
                    FilterChip(
                        selected = state.selectedCharacters.contains(item.id),
                        onClick = { vm.toggleCharacter(item.id) },
                        label = { Text(item.name) },
                    )
                }
            }
            Text("المكان", style = MaterialTheme.typography.titleMedium)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(state.locations, key = { it.id }) { item ->
                    FilterChip(selected = state.selectedLocation == item.id, onClick = { vm.selectLocation(item.id) }, label = { Text(item.name) })
                }
            }
            Text("الكاميرا", style = MaterialTheme.typography.titleMedium)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(listOf("wide", "medium", "close_up", "low_angle", "high_angle")) { value ->
                    FilterChip(selected = state.camera == value, onClick = { vm.setCamera(value) }, label = { Text(value) })
                }
            }
            Text("المزاج", style = MaterialTheme.typography.titleMedium)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(listOf("action", "epic", "comedic", "tense", "peaceful", "sad")) { value ->
                    FilterChip(selected = state.mood == value, onClick = { vm.setMood(value) }, label = { Text(value) })
                }
            }
            if (state.error != null) Text(state.error!!, color = MaterialTheme.colorScheme.error)
            Button(onClick = vm::compose, enabled = !state.loading && state.selectedCharacters.isNotEmpty(), modifier = Modifier.fillMaxWidth()) {
                if (state.loading) CircularProgressIndicator() else Text("🎨 بناء Prompt")
            }
            state.prompt?.let {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Prompt مولّد من بيانات المشروع", style = MaterialTheme.typography.titleSmall)
                        Text(it, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
