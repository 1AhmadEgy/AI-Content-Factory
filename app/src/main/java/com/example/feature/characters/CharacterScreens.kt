package com.example.feature.characters

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.core.theme.*
import com.example.data.remote.NetworkClient

@Composable
fun CharacterListScreen(onCharacterClick: (String) -> Unit, onSceneClick: () -> Unit, projectId: String? = null) {
    val vm: CharacterViewModel = viewModel(factory = CharacterViewModelFactory())
    val state by vm.state.collectAsState()
    Scaffold(containerColor = DarkBlue) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("CHARACTERS", color = PrimaryCyan, style = MaterialTheme.typography.labelMedium)
                    Text("Character Studio", color = TextLight, style = MaterialTheme.typography.headlineSmall)
                    Text("Manage your cast and keep every character consistent.", color = TextMuted)
                }
                IconButton(onClick = { vm.load(projectId) }) { Icon(Icons.Default.Refresh, "تحديث", tint = PrimaryCyan) }
            }
            when (val current = state) {
                CharacterListState.Loading -> NeonLoading()
                is CharacterListState.Error -> Box(Modifier.fillMaxSize(), Alignment.Center) { Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) { Text(current.message, color = MaterialTheme.colorScheme.error); Button(onClick = { vm.load(projectId) }) { Text("إعادة المحاولة") } } }
                is CharacterListState.Ready -> Column(Modifier.fillMaxSize()) {
                    LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(current.items, key = { it.id }) { character ->
                            NeonSectionCard {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) {
                                        Text(character.name, color = TextLight, style = MaterialTheme.typography.titleLarge)
                                        if (character.description.isNotBlank()) Text(character.description, color = TextMuted, style = MaterialTheme.typography.bodyMedium)
                                    }
                                    character.voice["voice"]?.toString()?.let { NeonStatusChip("🎤 $it") }
                                }
                                OutlinedButton(onClick = { onCharacterClick(character.id) }) { Text("Open Character") }
                            }
                        }
                    }
                    Button(onClick = onSceneClick, modifier = Modifier.fillMaxWidth().padding(16.dp), colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { Text("🎬 بناء مشهد", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold) }
                }
            }
        }
    }
}

@Composable
fun CharacterDetailScreen(characterId: String, onBack: () -> Unit, onScene: () -> Unit) {
    var character by remember { mutableStateOf<CharacterUi?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(characterId) { runCatching { NetworkClient.apiService.getCharacter(characterId).data }.onSuccess { character = it.toUi() }.onFailure { error = it.message ?: "تعذر تحميل الشخصية" } }
    Scaffold(containerColor = DarkBlue) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            item { TextButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null, tint = PrimaryCyan); Spacer(Modifier.width(6.dp)); Text("Back", color = PrimaryCyan) } }
            item { NeonHero(character?.name ?: "Character Profile", "Identity, appearance, voice and visual continuity") }
            when {
                error != null -> item { Text(error!!, color = MaterialTheme.colorScheme.error) }
                character == null -> item { Box(Modifier.fillMaxWidth().height(180.dp), Alignment.Center) { CircularProgressIndicator(color = PrimaryCyan) } }
                else -> {
                    item { NeonSectionCard { Text("DESCRIPTION", color = PrimaryCyan, style = MaterialTheme.typography.labelMedium); Text(character!!.description, color = TextLight) } }
                    if (character!!.appearance.isNotEmpty()) item { NeonSectionCard { Text("APPEARANCE", color = PrimaryCyan); Text(character!!.appearance, color = TextLight) } }
                    if (character!!.voice.isNotEmpty()) item { NeonSectionCard { Text("VOICE", color = PrimaryCyan); Text(character!!.voice.toString(), color = TextLight) } }
                    if (character!!.visualStyle.isNotEmpty()) item { NeonSectionCard { Text("VISUAL STYLE", color = PrimaryCyan); Text(character!!.visualStyle, color = TextLight) } }
                    item { Button(onClick = onScene, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { Text("Use Character in Scene") } }
                }
            }
        }
    }
}
