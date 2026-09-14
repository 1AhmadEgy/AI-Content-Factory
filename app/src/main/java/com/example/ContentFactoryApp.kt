package com.example

import android.app.Application
import com.example.data.repository.Graph

class ContentFactoryApp : Application() {
    override fun onCreate() {
        super.onCreate()
        AppContainer.initialize(this)
        Graph.provide(this)
    }
}
