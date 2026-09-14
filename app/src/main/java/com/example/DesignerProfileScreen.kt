package com.example

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val NeonPink = Color(0xFFFF1493)
private val NeonPurple = Color(0xFF8A2BE2)
private val NeonCyan = Color(0xFF00E5FF)
private val NeonGreen = Color(0xFF39FF14)
private val DesignerSurface = Color(0xFF03111F)
private val DesignerCard = Color(0xFF061A2B)

private data class Skill(val title: String, val subtitle: String, val icon: ImageVector)

@Composable
fun DesignerProfileScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    var copied by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize().background(DesignerSurface)) {
        DesignerTopBar(onBack = onBack) {
            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_SUBJECT, "AI Content Factory")
                putExtra(Intent.EXTRA_TEXT, "AI Content Factory — Designed & Developed by Ahmad Ragab\n$DESIGNER_EMAIL")
            }
            context.startActivity(Intent.createChooser(shareIntent, "Share designer profile"))
        }

        Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            DesignerHero()
            DesignerIdentityCard()

            Card(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = DesignerCard),
            ) {
                Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Surface(modifier = Modifier.size(52.dp), shape = RoundedCornerShape(16.dp), color = NeonPink.copy(alpha = 0.16f)) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(Icons.Filled.Email, contentDescription = null, tint = NeonPink, modifier = Modifier.size(28.dp))
                            }
                        }
                        Spacer(Modifier.width(14.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Email", color = Color(0xFF9EB4CC), style = MaterialTheme.typography.labelLarge)
                            Text(DESIGNER_EMAIL, color = Color.White, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyLarge)
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(8.dp).clip(CircleShape).background(NeonGreen))
                                Spacer(Modifier.width(7.dp))
                                Text("Available for contact", color = NeonCyan, style = MaterialTheme.typography.labelMedium)
                            }
                        }
                        IconButton(onClick = {
                            clipboard.setText(AnnotatedString(DESIGNER_EMAIL))
                            copied = true
                        }) {
                            Icon(Icons.Filled.ContentCopy, contentDescription = "Copy email", tint = Color.White)
                        }
                    }
                    if (copied) Text("Email copied", color = NeonGreen, style = MaterialTheme.typography.labelMedium)
                }
            }

            Button(
                onClick = {
                    context.startActivity(Intent(Intent.ACTION_SENDTO).apply {
                        data = Uri.parse("mailto:$DESIGNER_EMAIL?subject=AI%20Content%20Factory")
                    })
                },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).height(58.dp),
                shape = RoundedCornerShape(30.dp),
                colors = ButtonDefaults.buttonColors(containerColor = NeonPink),
            ) {
                Icon(Icons.Filled.Email, contentDescription = null)
                Spacer(Modifier.width(10.dp))
                Text("Contact the Designer", fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }

            Text("Skills & Focus", modifier = Modifier.padding(horizontal = 18.dp, vertical = 4.dp), color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)

            val skills = listOf(
                Skill("Creative", "Ideas into reality", Icons.Filled.Lightbulb),
                Skill("Development", "Clean & efficient", Icons.Filled.Code),
                Skill("Android", "Apps & tools", Icons.Filled.PhoneAndroid),
                Skill("AI Solutions", "Smarter content", Icons.Filled.AutoAwesome),
            )
            LazyRow(
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) { items(skills) { skill -> SkillCard(skill) } }

            Card(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color.Transparent),
            ) {
                Box(
                    modifier = Modifier.fillMaxWidth().background(
                        Brush.horizontalGradient(listOf(Color(0xFF12052A), Color(0xFF061A2B), Color(0xFF15051F))),
                        RoundedCornerShape(22.dp),
                    ).padding(20.dp),
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        Text("Thanks for using", color = Color.White, style = MaterialTheme.typography.titleMedium)
                        Text("AI Content Factory", color = NeonPink, fontWeight = FontWeight.Bold, fontSize = 22.sp)
                        HorizontalDivider(color = NeonPink.copy(alpha = 0.45f), modifier = Modifier.padding(vertical = 5.dp))
                        Text("Dream • Create • Innovate", color = Color(0xFFB9C8DB), style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }

            OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp), shape = RoundedCornerShape(18.dp)) {
                Icon(Icons.Filled.ArrowBack, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Back to App")
            }
        }
    }
}

@Composable
private fun DesignerTopBar(onBack: () -> Unit, onShare: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, contentDescription = "Back", tint = Color.White) }
        Text("Designer", modifier = Modifier.weight(1f), color = Color.White, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        IconButton(onClick = onShare) { Icon(Icons.Filled.Share, contentDescription = "Share", tint = Color.White) }
    }
    HorizontalDivider(color = NeonCyan.copy(alpha = 0.15f))
}

@Composable
private fun DesignerHero() {
    Box(modifier = Modifier.fillMaxWidth().height(270.dp).background(Brush.linearGradient(listOf(Color(0xFF1C0422), Color(0xFF06172B), Color(0xFF0A0120))))) {
        Column(modifier = Modifier.fillMaxSize().padding(horizontal = 22.dp, vertical = 18.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            Box(modifier = Modifier.size(142.dp).clip(CircleShape).background(Brush.linearGradient(listOf(NeonPink, NeonPurple, NeonCyan))).padding(4.dp)) {
                DesignerLogo(modifier = Modifier.fillMaxSize().clip(CircleShape))
            }
            Spacer(Modifier.height(12.dp))
            Text("AI Content Factory", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 24.sp)
            Text("Create  •  Edit  •  Generate", color = Color(0xFFB7C8DB), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun DesignerIdentityCard() {
    Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp), shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(containerColor = DesignerCard)) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("DESIGNED & DEVELOPED BY", color = NeonCyan, fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.3.sp)
            Text("Ahmad Ragab", color = Color.White, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            Text("Application Designer & Developer", color = Color(0xFFB6C7DA), style = MaterialTheme.typography.bodyLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(9.dp).clip(CircleShape).background(NeonGreen))
                Text("AI", color = NeonPink, fontWeight = FontWeight.Bold)
                Text("•", color = Color(0xFF61758C))
                Text("Android", color = NeonCyan, fontWeight = FontWeight.SemiBold)
                Text("•", color = Color(0xFF61758C))
                Text("Creative Design", color = Color.White)
            }
        }
    }
}

@Composable
private fun SkillCard(skill: Skill) {
    Card(modifier = Modifier.width(150.dp), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = DesignerCard)) {
        Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Surface(modifier = Modifier.size(48.dp), shape = RoundedCornerShape(15.dp), color = NeonPurple.copy(alpha = 0.18f)) {
                Box(contentAlignment = Alignment.Center) { Icon(skill.icon, contentDescription = null, tint = NeonPink, modifier = Modifier.size(26.dp)) }
            }
            Text(skill.title, color = Color.White, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Text(skill.subtitle, color = Color(0xFF93A9C0), style = MaterialTheme.typography.labelSmall, textAlign = TextAlign.Center)
        }
    }
}
