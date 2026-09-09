package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.feature.*
import com.example.core.theme.*
import com.example.core.theme.*
import com.example.core.theme.*
import com.example.feature.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme {
                MainScreen()
            }
        }
    }
}

@Composable
fun MainScreen() {
    val navController = rememberNavController()
    val viewModel: FactoryViewModel = viewModel()
    
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar(containerColor = DarkBlue) {
                NavigationBarItem(
                    icon = { Icon(Icons.Filled.VideoLibrary, contentDescription = "Projects") },
                    label = { Text("Projects") },
                    selected = currentRoute?.startsWith("projects") == true,
                    onClick = { navController.navigate("projects") { launchSingleTop = true } },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = DarkBlue,
                        selectedTextColor = PrimaryCyan,
                        indicatorColor = PrimaryCyan,
                        unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Filled.List, contentDescription = "Queue") },
                    label = { Text("Queue") },
                    selected = currentRoute == "queue",
                    onClick = { navController.navigate("queue") { launchSingleTop = true } },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = DarkBlue,
                        selectedTextColor = PrimaryCyan,
                        indicatorColor = PrimaryCyan,
                        unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                )
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "projects",
            modifier = Modifier.padding(padding)
        ) {
            composable("projects") {
                DashboardScreen(viewModel, onProjectClick = { id -> navController.navigate("project/$id") })
            }
            composable(
                "project/{projectId}",
                arguments = listOf(navArgument("projectId") { type = NavType.StringType })
            ) { backStackEntry ->
                val projectId = backStackEntry.arguments?.getString("projectId") ?: return@composable
                ProjectDetailScreen(
                    projectId = projectId,
                    viewModel = viewModel,
                    onBack = { navController.popBackStack() },
                    onSeriesClick = { id -> navController.navigate("series/$id") }
                )
            }
            composable(
                "series/{seriesId}",
                arguments = listOf(navArgument("seriesId") { type = NavType.StringType })
            ) { backStackEntry ->
                val seriesId = backStackEntry.arguments?.getString("seriesId") ?: return@composable
                SeriesDetailScreen(
                    seriesId = seriesId,
                    viewModel = viewModel,
                    onBack = { navController.popBackStack() },
                    onEpisodeClick = { id -> navController.navigate("episode/$id") }
                )
            }
            composable(
                "episode/{episodeId}",
                arguments = listOf(navArgument("episodeId") { type = NavType.StringType })
            ) { backStackEntry ->
                val episodeId = backStackEntry.arguments?.getString("episodeId") ?: return@composable
                EpisodeDetailScreen(
                    episodeId = episodeId,
                    viewModel = viewModel,
                    onBack = { navController.popBackStack() }
                )
            }
            composable("queue") {
                QueueScreen(viewModel)
            }
        }
    }
}
