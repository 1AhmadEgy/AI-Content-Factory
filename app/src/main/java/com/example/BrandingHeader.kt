package com.example

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.core.theme.DarkBlue

internal const val DESIGNER_EMAIL = "1ahmad.egy@gmail.com"

internal const val DESIGNER_LOGO_BASE64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAsICAoIBwsKCQoNDAsNERwSEQ8PESIZGhQcKSQrKigkJyctMkA3LTA9MCcnOEw5PUNFSElIKzZPVU5GVEBHSEX/2wBDAQwNDREPESESEiFFLicuRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUX/wAARCACIAKADASIAAhEBAxEB/8QAGwABAAIDAQEAAAAAAAAAAAAAAAUGAQMEAgf/xAA9EAABAwMCAwUECAQGAwAAAAABAAIDBAUREiExQVEGEyJhcRQjQrEyM1JigZHB0RWSobIkU1RjcpOiwuH/xAAaAQEAAgMBAAAAAAAAAAAAAAAAAgMBBAUG/8QAKREAAgIBAwMCBgMAAAAAAAAAAAECEQMEEiEFMUETUSIyYZGhwXHR8f/aAAwDAQACEQMRAD8A+RIiIAiIgCIrBa+yNZXxtlmcKaJ241DLiPRRlJRVstxYp5XtgrK+iu57CU2nasl1ddIwoO7dl6y1sMoxPAOL2DdvqFCOaEnSZfk0OfHHdKPBCIiK00wiIgCIiAIiIAiIgCIiAIiIAiIgLF2QtLK+udUTt1RU+CAeBdyX0FVjsNp/hU+Ppd9v+QVnXNzybmz1XT8cYYE15CwQCCCMg8QVlFQb5827T2ptruZ7kYgmGtg6dQoVXTt5p7qi+1l35bKlgEkADJK6mGTlBNnkdbjjjzyjHse44ZJQ8xsLgwanY5BeFcrRbhQ0eHgGWTd/7KAvNsNDUa4x7iQ+H7p6Kalbo13BpWRiIikQCIiAIiIAiIgCIiAInFdDtFOAwsa+T4tWcN8tlhsw3RM9kbsygrnQTu0w1GBqPBruS+hL5S+lAtLawt0l85jaB0Dcn5hSNr7W1tvjbFKBUQt2AecOA8itTLi9R7onW6f1GOOPpz7LyfRVgkNBJIAG5J5Kpnt5Bp2opNXQvGFB3btPW3Rhi2hgPFjOfqVVHTzb54Onk6lghG4u2Y7TXVt0uZMRzBCNDD16leuz1u76b2qUe7jPhzzd/wDFF0dK+sqWQx8XHc9B1VnrXNp6ZtvpniNxjc4uPwsAJJ25nBW46hHajzs8m+Us2QjbpfZnVJjo5CyNhxqHxH9l10FfHeaZ9HVgCUjYj4vMeagvZ6b/AFrf+t37L22mkhxVUcrZhEdRLMgs9Qd8efBZuJSs6vk01lJJRVLoZRuOB6jqtCtVTCy+2tk8QAnaNvXm1Vymopqqo7iJvjGcg7YwpJ+5OUafBoRZc1zHFrgQ4HBB5LCkQCIiAIiIAiLdDGNLpZB7tnL7R6LDdGG6DfcMEh+sd9AdPP8AZaiCDuPNdFK6CaujdXPcIC7MhYMnHQfJdlBF/Gu0UTdAayWXJYBs1g3x+AGFCU9tt+FZXKey3LslbJTtDR+wdmrPARh51Pd6kAn5qHtNsdcJ8uyIGfSPXyCnO0dS+/3ttFTH/D0uWl/LPxH9PwW6WopLLSNj4YHhYPpO81r6bcsS3d3b+7sh06E/QUsvd2/u7K5dbY+3zbZdC76Lv0Kj1bIrrQ3VhppgWF+2l/P0PVR0VhfHdBHLvTN8ZfyI6LZUvc3HC38J12uGO1Wx9bUDD3jIHPHIfioukqH1dwqJpDlzoJj6eB2yzebl7bPoiPuI9m+Z6rPZ5jZLvGx41Mcx4cOo0nKhPiEpP2KdRJLHKuyRs7PvInkYxkjpH6Md3HrOA4Ej8QCuqS2TWqSprKzELXtkY2MDLsvaQM42HEc1ab3FFR00DKNjIWh7BiIAcXsHJbLzpNhIGCRG8Y8tDly3q3NqSXEuDgPXOclNRpSdP34KP2frvZ6vuXn3c23o7krOynhhmlmawNfJjW7qqtZqWPU6tqdoINxn4nLRcbpNXynJLYgfCwH5+a6zVvg9PGW2PJLdoLZraayAbj6wDmOqralbTd30bxFOS+ndsQd9PovF4twpJhLDvTy7tI5eSkuOGRlT+JEaiIpFYREQBWF1NYJIYmuu0rAxo8IpycHn/VV5FXODnVNr+K/aKsmNzqpNV7V+0yzNHZh1K6jEsrZcA+2vjJyc8A3PTbgs0rbfbTI+0Vz6yulYYox3RYI88XZ8gqy1rnuDWglxOABzU8HR2Ckxs+ulHD7AVLweHJu/HH9FUdHfzTbXlOufx+EdEtRBYKQQxYkqXjJ9ep8lXJ55KiV0sri57uJKy5s9Q90jmyPc45LsEp7NP/kyfylbKVG890uy4NQySMcVN3G4zRUMVCZNU2kd87p9391GU7hTuMzh42bMaftdfwSCnfVy41AudvkuH6lGrMRUnxHuznXpkj4nh0bnMcObTgqx0tlgYGmQh55g6SP6OUgKSjhG8NM3/kxn6lZOhDpmSSuToqDquocMOnlIznBeVthmqqmURGpkAd9IukOAOeVbDBbzG57o6UtaMkhrdh+BVOq5Y5qmR8MbYoyfC1vIKO1exRqdCtOk207Om4VrZWspqbIpodm/ePUrgUvZ5A2duXNG2N3xj5hS15aJLU7duQ9pzqb8wFlcE4aT1cTy7u3iipKatFXHUQuttYcxv+rcfhPRddrtwYGyPLS74dMkZ/RYu93FODTUrgZeD34b4fIYHFGrJLSLHj9XJKvpXf8AJBVlJJRVLoZBuOB6jqtCno3tvtB3TyBWwjLSfjCgnNLHFrgQ4HBB5ImaElXKMIiLJEIi300scDu9c3W9v0GngD1P7ICRpmx2eAVM7Q6rePdRn4R1K1W2GS4V5mlOs6s5PMrgc+Wqn1PcXyPPE8yrjZ6IU1M08/n1KwkdDQ4PXyr2R3AGGHDA55aOAO5/NcFxuctJSuPcPjkf4WEuad+uxXc/vtXgdGG/eByoWuZJWTan4IaMNxw9VM7euzvFCo2n2RX44XSPyQXfmd1abbSughGzw5253eFDmARHcDY53A/UFTdLPG5g0aM43Axt+TFE5vTYwUm5dzgvN1mgm9kpC5rwMvfnf0Ch22yvqR3ggkfq+InirNUW6lrJu9lYQ/ABIPH/AMVulNPb6V0rmtDGDhpAyeQ4IbWXRyzTlPNL4V2+iKZU0s1I8MqIyxxGQD0WlbamofVVD5pD4nnPp5LWBk4CHnp7dz2diTtE2ioYO8LeX1mn/wBSrQ1/eN068752k3/tUHZaZwPeeIAcMGVvyGF1324PpKQQxyOEsvMOcSG8+PVDv6STwadzm+DReL33WqmpJCXcHyB2ceQ/dVtEQ42o1E9RPdP/AA9wzPglbLE4te05BCkq0R3OnNbA0NnYPfxj+4KKWyCeSmlEkTsOH5HyKw0UJ+Ga0Wyd0b5NUTdIduW/ZPT0WtZMBERAbIXvjkD43FrhwIUxS3CtdhvtL8D0UNHxUrRYBCF2LJOPytosFL38rcSSOcDxXS+ma1nBaaSVrWhbaiqbp4obTm5K5OyHrmBuVCSTyxPJjlew9WuIUnXVAcTuoWV2ShqzlT4Npuldw9rm/nK0y1U84xNNJIOOHOJWpEIPJOSpthemO0HOkH1z+i8ohAmIL97PG1jKRgA/3H/uo+trH11S6aTYnYAHYDoudEL56jJkjsk+AiIhQEREAREQBERAemnBXbBNpXBlew/CGU6JyOu0jivM1cXDiogSlYMpKE95ummLjxXK45QuysIQbsIiIYCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIgP/Z"

@Composable
private fun designerLogoBitmap() = remember {
    runCatching {
        val bytes = Base64.decode(DESIGNER_LOGO_BASE64, Base64.DEFAULT)
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
    }.getOrNull()
}

@Composable
fun DesignerLogo(modifier: Modifier = Modifier, contentDescription: String = "شعار المصمم - أحمد رجب") {
    val bitmap = designerLogoBitmap()
    if (bitmap != null) {
        Image(bitmap = bitmap, contentDescription = contentDescription, modifier = modifier, contentScale = ContentScale.Fit)
    } else {
        Surface(modifier = modifier, shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
            Box(contentAlignment = Alignment.Center) { Text("AI", style = MaterialTheme.typography.labelLarge) }
        }
    }
}

@Composable
fun BrandingHeader(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    Card(modifier = modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = DarkBlue), shape = RoundedCornerShape(bottomStart = 18.dp, bottomEnd = 18.dp)) {
        Row(modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            DesignerLogo(modifier = Modifier.size(58.dp).clip(RoundedCornerShape(14.dp)))
            Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                Text("مصنع المحتوى بالذكاء الاصطناعي", style = MaterialTheme.typography.titleMedium)
                Text("تصميم وتطوير أحمد رجب", style = MaterialTheme.typography.labelMedium)
                Text(DESIGNER_EMAIL, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary, modifier = Modifier.clickable { context.startActivity(Intent(Intent.ACTION_SENDTO).apply { data = Uri.parse("mailto:$DESIGNER_EMAIL") }) })
            }
        }
    }
}
