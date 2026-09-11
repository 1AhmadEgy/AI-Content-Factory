package com.example.feature.characters

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.data.remote.NetworkClient

@Composable
fun CharacterListScreen(
    onCharacterClick: (String) -> Unit,
    onSceneClick: () -> Unit,
    projectId: String? = null,
) {
    val vm: CharacterViewModel = viewModel(factory = CharacterViewModelFactory())
    val state by vm.state.collectAsState()
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("الشخصيات") }, actions = {
                IconButton(onClick = { vm.load(projectId) }) { Icon(Icons.Default.Refresh, contentDescription = "تحديث") }
            })
        },
    ) { padding ->
        when (val current = state) {
            CharacterListState.Loading -> Box(Modifier.fillMaxSize().padding(padding), Alignment.Center) { CircularProgressIndicator() }
            is CharacterListState.Error -> Box(Modifier.fillMaxSize().padding(padding), Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(current.message, color = MaterialTheme.colorScheme.error)
                    Button(onClick = { vm.load(projectId) }) { Text("إعادة المحاولة") }
                }
            }
            is CharacterListState.Ready -> Column(Modifier.fillMaxSize().padding(padding)) {
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    items(current.items, key = { it.id }) { character ->
                        Card(onClick = { onCharacterClick(character.id) }, modifier = Modifier.fillMaxWidth()) {
                            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(character.name, style = MaterialTheme.typography.titleLarge)
                                    if (character.description.isNotBlank()) Text(character.description, style = MaterialTheme.typography.bodyMedium)
                                }
                                character.voice["voice"]?.toString()?.let { AssistChip(onClick = {}, label = { Text("🎤 $it") }) }
                            }
                        }
                    }
                }
                Button(onClick = onSceneClick, modifier = Modifier.fillMaxWidth().padding(16.dp)) { Text("🎬 بناء مشهد") }
            }
        }
    }
}

@Composable
fun CharacterDetailScreen(characterId: String, onBack: () -> Unit, onScene: () -> Unit) {
    var character by remember { mutableStateOf<CharacterUi?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(characterId) {
        runCatching { NetworkClient.apiService.getCharacter(characterId).data }
            .onSuccess { character = it.toUi() }
            .onFailure { error = it.message ?: "تعذر تحميل الشخصية" }
    }
    Scaffold(topBar = {
        TopAppBar(title = { Text(character?.name ?: "تفاصيل الشخصية") }, navigationIcon = {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = "رجوع") }
        })
    }) { padding ->
        when {
            error != null -> Box(Modifier.fillMaxSize().padding(padding), Alignment.Center) { Text(error!!, color = MaterialTheme.colorScheme.error) }
            character == null -> Box(Modifier.fillMaxSize().padding(padding), Alignment.Center) { CircularProgressIndicator() }
            else -> Column(Modifier.fillMaxSize().padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(character!!.name, style = MaterialTheme.typography.headlineMedium)
                Text(character!!.description)
                if (character!!.appearance.isNotEmpty()) Text("المظهر: ${character!!.appearance}")
                if (character!!.voice.isNotEmpty()) Text("الصوت: ${character!!.voice}")
                if (character!!.visualStyle.isNotEmpty()) Text("الأسلوب البصري: ${character!!.visualStyle}")
                Spacer(Modifier.weight(1f))
                Button(onClick = onScene, modifier = Modifier.fillMaxWidth()) { Text("استخدام الشخصية في مشهد") }
            }
        }
    }
}
