package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.runtime.CompositionLocalProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.core.theme.AppTheme
import com.example.core.theme.DarkBlue
import com.example.core.theme.PrimaryCyan
import com.example.feature.*
import com.example.feature.characters.CharacterDetailScreen
import com.example.feature.characters.CharacterListScreen
import com.example.feature.scenes.SceneBuilderScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
                AppTheme { MainScreen() }
            }
        }
    }
}

@Composable
fun MainScreen() {
    val navController = rememberNavController()
    val viewModel: FactoryViewModel = viewModel()
    val error by viewModel.error.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    LaunchedEffect(error) {
        error?.let {
            snackbarHostState.showSnackbar(message = it, duration = SnackbarDuration.Long)
            viewModel.clearError()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            NavigationBar(containerColor = DarkBlue) {
                NavigationBarItem(
                    icon = { Icon(Icons.Filled.VideoLibrary, contentDescription = "المشاريع") },
                    label = { Text("المشاريع") },
                    selected = currentRoute?.startsWith("projects") == true,
                    onClick = { navController.navigate("projects") { launchSingleTop = true } },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan),
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Filled.List, contentDescription = "الشخصيات") },
                    label = { Text("الشخصيات") },
                    selected = currentRoute == "characters" || currentRoute?.startsWith("character/") == true || currentRoute == "scene-builder",
                    onClick = { navController.navigate("characters") { launchSingleTop = true } },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan),
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Filled.List, contentDescription = "مركز التحكم") },
                    label = { Text("التحكم") },
                    selected = currentRoute == "control",
                    onClick = { navController.navigate("control") { launchSingleTop = true } },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = DarkBlue, selectedTextColor = PrimaryCyan, indicatorColor = PrimaryCyan),
                )
            }
        },
    ) { padding ->
        NavHost(navController = navController, startDestination = "projects", modifier = Modifier.padding(padding)) {
            composable("projects") { DashboardScreen(viewModel, onProjectClick = { id -> navController.navigate("project/$id") }) }
            composable("project/{projectId}", arguments = listOf(navArgument("projectId") { type = NavType.StringType })) { backStackEntry ->
                val projectId = backStackEntry.arguments?.getString("projectId") ?: return@composable
                ProjectDetailScreen(projectId, viewModel, onBack = { navController.popBackStack() }, onSeriesClick = { id -> navController.navigate("series/$id") }, onSeriesControlClick = { navController.navigate("series-control/$projectId") })
            }
            composable("series/{seriesId}", arguments = listOf(navArgument("seriesId") { type = NavType.StringType })) { backStackEntry ->
                val seriesId = backStackEntry.arguments?.getString("seriesId") ?: return@composable
                SeriesDetailScreen(seriesId, viewModel, onBack = { navController.popBackStack() }, onEpisodeClick = { id -> navController.navigate("episode/$id") })
            }
            composable("series-control/{projectId}", arguments = listOf(navArgument("projectId") { type = NavType.StringType })) { backStackEntry ->
                val projectId = backStackEntry.arguments?.getString("projectId") ?: return@composable
                SeriesControlScreen(projectId, onBack = { navController.popBackStack() })
            }
            composable("episode/{episodeId}", arguments = listOf(navArgument("episodeId") { type = NavType.StringType })) { backStackEntry ->
                val episodeId = backStackEntry.arguments?.getString("episodeId") ?: return@composable
                EpisodeDetailScreen(episodeId, viewModel, onBack = { navController.popBackStack() })
            }
            composable("characters") { CharacterListScreen(onCharacterClick = { id -> navController.navigate("character/$id") }, onSceneClick = { navController.navigate("scene-builder") }) }
            composable("character/{characterId}", arguments = listOf(navArgument("characterId") { type = NavType.StringType })) { backStackEntry ->
                val characterId = backStackEntry.arguments?.getString("characterId") ?: return@composable
                CharacterDetailScreen(characterId, onBack = { navController.popBackStack() }, onScene = { navController.navigate("scene-builder") })
            }
            composable("scene-builder") { SceneBuilderScreen(onBack = { navController.popBackStack() }) }
            composable("control") { ControlCenterScreen() }
        }
    }
}
