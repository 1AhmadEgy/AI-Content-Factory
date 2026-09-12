package com.example.feature.scenes

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.data.remote.CharacterDto
import com.example.data.remote.ComposeShotRequest
import com.example.data.remote.LocationDto
import com.example.data.remote.NetworkClient
import com.example.data.remote.ShotCharacterRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class SceneCharacter(val id: String, val name: String)
data class SceneLocation(val id: String, val name: String)

data class SceneUiState(
    val characters: List<SceneCharacter> = emptyList(),
    val locations: List<SceneLocation> = emptyList(),
    val selectedCharacters: Set<String> = emptySet(),
    val selectedLocation: String? = null,
    val camera: String = "medium",
    val mood: String? = null,
    val loading: Boolean = false,
    val prompt: String? = null,
    val error: String? = null,
)

class SceneBuilderRepository {
    // Defer Retrofit construction until the coroutine's guarded request path.
    // A missing backend configuration must become UI error state, never a screen crash.
    private val api by lazy { NetworkClient.apiService }

    suspend fun load(): Pair<List<SceneCharacter>, List<SceneLocation>> {
        val chars = api.listCharacters().data.map(CharacterDto::toScene)
        val locs = api.listLocations().data.map(LocationDto::toScene)
        return chars to locs
    }

    suspend fun compose(characterIds: List<String>, locationId: String?, camera: String, mood: String?): String {
        val response = api.composeShot(
            ComposeShotRequest(
                characters = characterIds.mapIndexed { index, id -> ShotCharacterRequest(characterId = id, positionOrder = index) },
                locationId = locationId,
                cameraAngle = camera,
                mood = mood,
            )
        )
        return response.data.prompt
    }
}

private fun CharacterDto.toScene() = SceneCharacter(id, name)
private fun LocationDto.toScene() = SceneLocation(id, name)

class SceneBuilderViewModel(private val repository: SceneBuilderRepository) : ViewModel() {
    private val _state = MutableStateFlow(SceneUiState())
    val state: StateFlow<SceneUiState> = _state.asStateFlow()

    init { load() }

    private fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repository.load() }
                .onSuccess { (chars, locs) -> _state.value = _state.value.copy(characters = chars, locations = locs, loading = false) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message ?: "تعذر تحميل البيانات") }
        }
    }

    fun toggleCharacter(id: String) {
        val next = _state.value.selectedCharacters.toMutableSet()
        if (!next.add(id)) next.remove(id)
        _state.value = _state.value.copy(selectedCharacters = next, prompt = null)
    }

    fun selectLocation(id: String) = _state.value.let { _state.value = it.copy(selectedLocation = id, prompt = null) }
    fun setCamera(value: String) = _state.value.let { _state.value = it.copy(camera = value, prompt = null) }
    fun setMood(value: String) = _state.value.let { _state.value = it.copy(mood = value, prompt = null) }

    fun compose() {
        val current = _state.value
        if (current.selectedCharacters.isEmpty()) {
            _state.value = current.copy(error = "اختر شخصية واحدة على الأقل")
            return
        }
        viewModelScope.launch {
            _state.value = current.copy(loading = true, error = null)
            runCatching { repository.compose(current.selectedCharacters.toList(), current.selectedLocation, current.camera, current.mood) }
                .onSuccess { _state.value = _state.value.copy(loading = false, prompt = it) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message ?: "فشل بناء الـPrompt") }
        }
    }
}

class SceneBuilderViewModelFactory(
    private val repository: SceneBuilderRepository = SceneBuilderRepository(),
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(SceneBuilderViewModel::class.java)) return SceneBuilderViewModel(repository) as T
        throw IllegalArgumentException("Unknown ViewModel: ${modelClass.name}")
    }
}
