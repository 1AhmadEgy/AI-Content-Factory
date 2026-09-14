package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.example.core.theme.AppTheme
import com.example.core.theme.DarkBlue
import com.example.core.theme.PrimaryCyan
import com.example.feature.*
import com.example.feature.characters.CharacterDetailScreen
import com.example.feature.characters.CharacterListScreen
import com.example.feature.scenes.SceneBuilderScreen

class MainActivity : ComponentActivity() { override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { AppTheme { MainScreen() } } } }

@Composable
fun MainScreen() {
    val navController = rememberNavController(); val viewModel: FactoryViewModel = viewModel(); val entry by navController.currentBackStackEntryAsState(); val route = entry?.destination?.route
    val snackbarHostState = remember { SnackbarHostState() }; val errorMessage by viewModel.errorMessage.collectAsState()
    LaunchedEffect(errorMessage) { errorMessage?.let { snackbarHostState.showSnackbar(it); viewModel.clearError() } }
    Scaffold(topBar = { if (route != "designer" && route != "settings") BrandingHeader() }, snackbarHost = { SnackbarHost(snackbarHostState) }, bottomBar = {
        NavigationBar(containerColor = DarkBlue) {
            NavigationBarItem(icon = { Icon(Icons.Filled.VideoLibrary, "Projects") }, label = { Text("Projects") }, selected = route?.startsWith("projects") == true, onClick = { navController.navigate("projects") { launchSingleTop = true } }, colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan))
            NavigationBarItem(icon = { Icon(Icons.Filled.List, "Characters") }, label = { Text("Characters") }, selected = route == "characters" || route?.startsWith("character/") == true || route == "scene-builder", onClick = { navController.navigate("characters") { launchSingleTop = true } }, colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan))
            NavigationBarItem(icon = { Icon(Icons.Filled.List, "Control") }, label = { Text("Control") }, selected = route == "control", onClick = { navController.navigate("control") { launchSingleTop = true } }, colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan))
            NavigationBarItem(icon = { Icon(Icons.Filled.Info, "Designer") }, label = { Text("Designer") }, selected = route == "designer", onClick = { navController.navigate("designer") { launchSingleTop = true } }, colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan))
            NavigationBarItem(icon = { Icon(Icons.Filled.Settings, "Settings") }, label = { Text("Settings") }, selected = route == "settings", onClick = { navController.navigate("settings") { launchSingleTop = true } }, colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan))
        }
    }) { padding ->
        NavHost(navController, startDestination = "projects", modifier = Modifier.padding(padding)) {
            composable("projects") { NeonDashboardScreen(viewModel, onProjectClick = { navController.navigate("project/$it") }) }
            composable("project/{projectId}", arguments = listOf(navArgument("projectId") { type = NavType.StringType })) { e -> val id = e.arguments?.getString("projectId") ?: return@composable; NeonProjectDetailScreen(id, viewModel, { navController.popBackStack() }, { navController.navigate("series/$it") }, { navController.navigate("series-control/$id") }) }
            composable("series/{seriesId}", arguments = listOf(navArgument("seriesId") { type = NavType.StringType })) { e -> val id = e.arguments?.getString("seriesId") ?: return@composable; NeonSeriesDetailScreen(id, viewModel, { navController.popBackStack() }, { navController.navigate("episode/$it") }) }
            composable("series-control/{projectId}", arguments = listOf(navArgument("projectId") { type = NavType.StringType })) { e -> val id = e.arguments?.getString("projectId") ?: return@composable; SeriesControlScreen(id, { navController.popBackStack() }) }
            composable("episode/{episodeId}", arguments = listOf(navArgument("episodeId") { type = NavType.StringType })) { e -> val id = e.arguments?.getString("episodeId") ?: return@composable; NeonEpisodeDetailScreen(id, viewModel, { navController.popBackStack() }) }
            composable("characters") { CharacterListScreen({ navController.navigate("character/$it") }, { navController.navigate("scene-builder") }) }
            composable("character/{characterId}", arguments = listOf(navArgument("characterId") { type = NavType.StringType })) { e -> val id = e.arguments?.getString("characterId") ?: return@composable; CharacterDetailScreen(id, { navController.popBackStack() }, { navController.navigate("scene-builder") }) }
            composable("scene-builder") { SceneBuilderScreen { navController.popBackStack() } }
            composable("control") { NeonControlCenterScreen() }
            composable("designer") { DesignerProfileScreen { navController.popBackStack() } }
            composable("settings") { SettingsScreen { navController.popBackStack() } }
        }
    }
}
