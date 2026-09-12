package com.example

import android.app.Application
import com.example.data.remote.NetworkClient
import com.example.data.repository.Graph

class ContentFactoryApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NetworkClient.initialize(this)
        Graph.provide(this)
    }
}
