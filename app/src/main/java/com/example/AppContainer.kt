package com.example

import android.content.Context

object AppContainer {
    private lateinit var applicationContext: Context
    fun initialize(context: Context) { applicationContext = context.applicationContext }
    fun context(): Context = applicationContext
}
