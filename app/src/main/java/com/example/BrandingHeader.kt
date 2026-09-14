package com.example

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.example.core.theme.DarkBlue

private const val DESIGNER_EMAIL = "1ahmad.egy@gmail.com"

@Composable
fun BrandingHeader(modifier: Modifier = Modifier) {
    val context = LocalContext.current

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = DarkBlue),
        shape = RoundedCornerShape(bottomStart = 18.dp, bottomEnd = 18.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Image(
                painter = painterResource(id = R.drawable.designer_logo),
                contentDescription = "AI Content Factory logo - Ahmad Ragab",
                modifier = Modifier
                    .size(58.dp)
                    .clip(RoundedCornerShape(14.dp)),
                contentScale = ContentScale.Fit,
            )

            Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                Text(
                    text = "AI Content Factory",
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text = "Designed by Ahmad Ragab",
                    style = MaterialTheme.typography.labelMedium,
                )
                Text(
                    text = DESIGNER_EMAIL,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable {
                        val intent = Intent(Intent.ACTION_SENDTO).apply {
                            data = Uri.parse("mailto:$DESIGNER_EMAIL")
                        }
                        context.startActivity(intent)
                    },
                )
            }
        }
    }
}
