package com.example.feature

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.example.AppContainer
import com.example.core.theme.DarkBlue
import com.example.core.theme.PrimaryCyan

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onBack: () -> Unit) {
    val store = remember { AppContainer.apiKeyStore() }
    var apiKey by remember { mutableStateOf("") }
    var visible by remember { mutableStateOf(false) }
    var configured by remember { mutableStateOf(store.isConfigured()) }
    var message by remember { mutableStateOf<String?>(null) }
    Scaffold(topBar = { TopAppBar(title = { Text("واجهة البرمجة والخادم") }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, "رجوع") } }) }) { padding ->
        Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(padding).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("مفتاح واجهة الخادم")
            Text(if (configured) "تم حفظ مفتاح الواجهة بأمان على هذا الجهاز." else "لم يتم إعداد مفتاح الواجهة بعد.")
            OutlinedTextField(value = apiKey, onValueChange = { apiKey = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("مفتاح الواجهة") }, placeholder = { Text("ألصق مفتاح واجهة الخادم") }, leadingIcon = { Icon(Icons.Filled.Key, "مفتاح الواجهة") }, visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(), trailingIcon = { IconButton(onClick = { visible = !visible }) { Icon(if (visible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility, "تبديل إظهار المفتاح") } })
            Button(onClick = { runCatching { store.saveApiKey(apiKey); apiKey = ""; configured = true; message = "تم حفظ مفتاح الواجهة بأمان." }.onFailure { message = "تعذر حفظ مفتاح الواجهة." } }, enabled = apiKey.isNotBlank(), modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { Text("حفظ مفتاح الواجهة") }
            Button(onClick = { store.clearApiKey(); apiKey = ""; configured = false; message = "تم حذف مفتاح الواجهة." }, enabled = configured, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = DarkBlue, contentColor = PrimaryCyan)) { Icon(Icons.Filled.Delete, null); Text("  حذف مفتاح الواجهة") }
            message?.let { Text(it) }
            Text("الأمان: يتم تشفير المفتاح باستخدام Android Keystore، ولا يُكتب في الشيفرة المصدرية أو يُعرض بعد الحفظ.")
        }
    }
}
