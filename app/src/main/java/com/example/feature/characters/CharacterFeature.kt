package com.example.feature.characters

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.data.remote.CharacterDto
import com.example.data.remote.NetworkClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class CharacterUi(
    val id: String,
    val projectId: String,
    val name: String,
    val description: String,
    val appearance: Map<String, Any?>,
    val voice: Map<String, Any?>,
    val visualStyle: Map<String, Any?>,
)

fun CharacterDto.toUi() = CharacterUi(id, projectId, name, description, appearance, voice, visualStyle)

class CharacterRepository {
    private val api = NetworkClient.apiService

    suspend fun list(projectId: String? = null): List<CharacterUi> =
        api.listCharacters(projectId).data.map(CharacterDto::toUi)

    suspend fun get(id: String): CharacterUi = api.getCharacter(id).data.toUi()
}

sealed interface CharacterListState {
    data object Loading : CharacterListState
    data class Ready(val items: List<CharacterUi>) : CharacterListState
    data class Error(val message: String) : CharacterListState
}

class CharacterViewModel(private val repository: CharacterRepository) : ViewModel() {
    private val _state = MutableStateFlow<CharacterListState>(CharacterListState.Loading)
    val state: StateFlow<CharacterListState> = _state.asStateFlow()

    init { load() }

    fun load(projectId: String? = null) {
        viewModelScope.launch {
            _state.value = CharacterListState.Loading
            _state.value = runCatching { CharacterListState.Ready(repository.list(projectId)) }
                .getOrElse { CharacterListState.Error(it.message ?: "تعذر تحميل الشخصيات") }
        }
    }
}

class CharacterViewModelFactory(
    private val repository: CharacterRepository = CharacterRepository(),
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(CharacterViewModel::class.java)) return CharacterViewModel(repository) as T
        throw IllegalArgumentException("Unknown ViewModel: ${modelClass.name}")
    }
}
