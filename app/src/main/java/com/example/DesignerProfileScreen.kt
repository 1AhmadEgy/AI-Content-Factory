package com.example

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.core.theme.DarkBlue

@Composable
fun DesignerProfileScreen(onBack: () -> Unit) {
    val context = LocalContext.current

    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = DarkBlue),
            shape = RoundedCornerShape(24.dp),
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                DesignerLogo(
                    modifier = Modifier.size(180.dp),
                    contentDescription = "AI Content Factory designer logo",
                )
                Text("AI Content Factory", style = MaterialTheme.typography.headlineSmall)
                Text("Designed & Developed by", style = MaterialTheme.typography.bodyMedium)
                Text("Ahmad Ragab", style = MaterialTheme.typography.headlineMedium)
                Text(
                    DESIGNER_EMAIL,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }

        Text(
            "This application was designed and developed by Ahmad Ragab.",
            style = MaterialTheme.typography.bodyLarge,
        )

        Button(
            onClick = {
                context.startActivity(Intent(Intent.ACTION_SENDTO).apply {
                    data = Uri.parse("mailto:$DESIGNER_EMAIL?subject=AI%20Content%20Factory")
                })
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Contact the Designer")
        }

        Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
            Text("Back")
        }
    }
}
